from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.config.constants import (
    EVENT_ROUTE_COMPLETED,
    EVENT_ROUTE_DEVIATION,
    EVENT_ROUTE_DEVIATION_RECOVERED,
    EVENT_ROUTE_STOP_ARRIVAL,
    EVENT_ROUTE_STOP_DEPARTURE,
)
from app.database.repositories.journey_repository import JourneyRepository
from app.database.repositories.route_repository import RouteRepository
from app.database.repositories.route_stop_repository import RouteStopRepository
from app.database.repositories.vehicle_state_repository import VehicleStateRepository
from app.models.vehicle_state import VehicleState
from app.services.event_alert_service import process_event_for_alert
from app.services.event_service import create_event

from .geometry import (
    haversine_m,
    parse_route_geometry,
    project_point_to_route,
    route_length_m,
)


DEFAULT_DEVIATION_THRESHOLD_M = 100.0
STOP_ARRIVAL_THRESHOLD_M = 75.0
ROUTE_COMPLETION_THRESHOLD_M = 75.0


@dataclass
class RouteProgressResult:
    vehicle_id: str
    route_id: str
    route_version: int

    progress_percent: float
    distance_travelled_m: float
    distance_remaining_m: float

    distance_from_route_m: float
    deviation_threshold_m: float
    deviation_status: str

    current_stop_id: str | None
    current_stop_name: str | None
    next_stop_id: str | None
    next_stop_name: str | None

    completed_stop_ids: list[str]
    route_completed: bool


def _evaluate_stop_lifecycle(
    db: Session,
    route_stops,
    current_latitude: float,
    current_longitude: float,
    route_points,
    vehicle_id: str,
    sequence_number: int | None,
    mutate: bool = False,
):
    """
    Ordered route-stop state machine.

    planned -> arrived -> departed -> completed

    Arrival/departure timestamps are persisted only when mutate=True.
    Read-only API calculations therefore remain side-effect free.
    """

    projection = project_point_to_route(
        current_latitude,
        current_longitude,
        route_points,
    )

    ordered = sorted(route_stops, key=lambda stop: stop.sequence)

    current_stop = None
    next_stop = None
    completed_ids = []

    now = datetime.utcnow()

    for stop in ordered:
        stop_projection = project_point_to_route(
            stop.latitude,
            stop.longitude,
            route_points,
        )

        distance_to_stop = haversine_m(
            current_latitude,
            current_longitude,
            stop.latitude,
            stop.longitude,
        )

        passed_stop = (
            projection.along_route_m
            >= stop_projection.along_route_m
            + STOP_ARRIVAL_THRESHOLD_M
        )

        inside_stop_zone = (
            distance_to_stop <= STOP_ARRIVAL_THRESHOLD_M
        )

        if mutate:
            previous_status = stop.status

            # Arrival.
            if (
                stop.status == "planned"
                and inside_stop_zone
            ):
                stop.status = "arrived"
                stop.actual_arrival_at = now

                event = create_event(
                    db=db,
                    vehicle_id=vehicle_id,
                    event_type=EVENT_ROUTE_STOP_ARRIVAL,
                    severity="info",
                    message=(
                        f"Vehicle arrived at route stop "
                        f"{stop.stop_id} ({stop.name})."
                    ),
                    sequence_number=sequence_number,
                )
                process_event_for_alert(db=db, event=event)

            # Departure / completion.
            if (
                stop.status == "arrived"
                and passed_stop
            ):
                stop.status = "completed"
                stop.actual_departure_at = now

                event = create_event(
                    db=db,
                    vehicle_id=vehicle_id,
                    event_type=EVENT_ROUTE_STOP_DEPARTURE,
                    severity="info",
                    message=(
                        f"Vehicle departed route stop "
                        f"{stop.stop_id} ({stop.name})."
                    ),
                    sequence_number=sequence_number,
                )
                process_event_for_alert(db=db, event=event)

            # A vehicle may have skipped a telemetry sample while
            # passing a stop. Preserve lifecycle correctness.
            elif (
                stop.status == "planned"
                and passed_stop
            ):
                stop.status = "completed"
                stop.actual_arrival_at = now
                stop.actual_departure_at = now

                arrival_event = create_event(
                    db=db,
                    vehicle_id=vehicle_id,
                    event_type=EVENT_ROUTE_STOP_ARRIVAL,
                    severity="info",
                    message=(
                        f"Vehicle passed route stop "
                        f"{stop.stop_id} ({stop.name}) between telemetry samples."
                    ),
                    sequence_number=sequence_number,
                )
                process_event_for_alert(
                    db=db,
                    event=arrival_event,
                )

                departure_event = create_event(
                    db=db,
                    vehicle_id=vehicle_id,
                    event_type=EVENT_ROUTE_STOP_DEPARTURE,
                    severity="info",
                    message=(
                        f"Vehicle departed route stop "
                        f"{stop.stop_id} ({stop.name})."
                    ),
                    sequence_number=sequence_number,
                )
                process_event_for_alert(
                    db=db,
                    event=departure_event,
                )

            if stop.status == "completed":
                completed_ids.append(stop.stop_id)

        else:
            if stop.status == "completed" or passed_stop:
                completed_ids.append(stop.stop_id)

        if (
            current_stop is None
            and inside_stop_zone
            and stop.status != "completed"
        ):
            current_stop = stop

        if (
            next_stop is None
            and stop_projection.along_route_m
            > projection.along_route_m
            and stop.status != "completed"
        ):
            next_stop = stop

    return current_stop, next_stop, completed_ids


def calculate_route_progress(
    db: Session,
    vehicle_id: str,
    route_id: str,
    deviation_threshold_m: float = DEFAULT_DEVIATION_THRESHOLD_M,
) -> RouteProgressResult:

    state = VehicleStateRepository(db).get_by_vehicle_id(vehicle_id)

    if state is None:
        raise ValueError("Vehicle state not found")

    route = RouteRepository(db).get_by_route_id(route_id)

    if route is None:
        raise ValueError("Route not found")

    route_points = parse_route_geometry(route.geometry)
    route_length = route_length_m(route_points)

    if route_length <= 0:
        raise ValueError("Route geometry has zero length")

    projection = project_point_to_route(
        state.latitude,
        state.longitude,
        route_points,
    )

    distance_travelled = min(
        max(projection.along_route_m, 0.0),
        route_length,
    )

    distance_remaining = max(
        route_length - distance_travelled,
        0.0,
    )

    progress_percent = min(
        max((distance_travelled / route_length) * 100.0, 0.0),
        100.0,
    )

    stops = RouteStopRepository(db).list_by_route(route_id)

    current_stop, next_stop, completed_ids = _evaluate_stop_lifecycle(
        db=db,
        route_stops=stops,
        current_latitude=state.latitude,
        current_longitude=state.longitude,
        route_points=route_points,
        vehicle_id=vehicle_id,
        sequence_number=state.sequence_number,
        mutate=False,
    )

    deviation_status = (
        "DEVIATED"
        if projection.distance_from_route_m > deviation_threshold_m
        else "NORMAL"
    )

    route_completed = (
        distance_remaining <= ROUTE_COMPLETION_THRESHOLD_M
        or progress_percent >= 99.0
    )

    return RouteProgressResult(
        vehicle_id=vehicle_id,
        route_id=route_id,
        route_version=route.version,
        progress_percent=round(progress_percent, 3),
        distance_travelled_m=round(distance_travelled, 3),
        distance_remaining_m=round(distance_remaining, 3),
        distance_from_route_m=round(
            projection.distance_from_route_m,
            3,
        ),
        deviation_threshold_m=deviation_threshold_m,
        deviation_status=deviation_status,
        current_stop_id=current_stop.stop_id if current_stop else None,
        current_stop_name=current_stop.name if current_stop else None,
        next_stop_id=next_stop.stop_id if next_stop else None,
        next_stop_name=next_stop.name if next_stop else None,
        completed_stop_ids=completed_ids,
        route_completed=route_completed,
    )


def _active_route_for_vehicle(
    db: Session,
    vehicle_id: str,
) -> str | None:

    state = VehicleStateRepository(db).get_by_vehicle_id(vehicle_id)

    if state is None or not state.convoy_id:
        return None

    journeys = JourneyRepository(db).list_all()

    candidates = [
        journey
        for journey in journeys
        if journey.convoy_id == state.convoy_id
        and journey.route_id is not None
        and journey.status in {"planned", "active", "paused"}
    ]

    if not candidates:
        return None

    candidates.sort(
        key=lambda journey: journey.id,
        reverse=True,
    )

    return candidates[0].route_id


def calculate_vehicle_route_progress(
    db: Session,
    vehicle_id: str,
    deviation_threshold_m: float = DEFAULT_DEVIATION_THRESHOLD_M,
) -> RouteProgressResult:

    route_id = _active_route_for_vehicle(
        db,
        vehicle_id,
    )

    if route_id is None:
        raise ValueError(
            "No assigned route found for the vehicle's active journey"
        )

    return calculate_route_progress(
        db=db,
        vehicle_id=vehicle_id,
        route_id=route_id,
        deviation_threshold_m=deviation_threshold_m,
    )


def evaluate_route_progress(
    db: Session,
    current_state: VehicleState,
    previous_latitude: float | None = None,
    previous_longitude: float | None = None,
    deviation_threshold_m: float = DEFAULT_DEVIATION_THRESHOLD_M,
) -> RouteProgressResult | None:

    if not current_state.convoy_id:
        return None

    route_id = _active_route_for_vehicle(
        db,
        current_state.vehicle_id,
    )

    if route_id is None:
        return None

    route = RouteRepository(db).get_by_route_id(route_id)

    if route is None:
        return None

    points = parse_route_geometry(route.geometry)

    result = calculate_route_progress(
        db=db,
        vehicle_id=current_state.vehicle_id,
        route_id=route_id,
        deviation_threshold_m=deviation_threshold_m,
    )

    previous_status = None
    previous_completed = False

    if (
        previous_latitude is not None
        and previous_longitude is not None
    ):
        previous_projection = project_point_to_route(
            previous_latitude,
            previous_longitude,
            points,
        )

        previous_status = (
            "DEVIATED"
            if previous_projection.distance_from_route_m
            > deviation_threshold_m
            else "NORMAL"
        )

        previous_length = route_length_m(points)
        previous_remaining = max(
            previous_length
            - previous_projection.along_route_m,
            0.0,
        )

        previous_completed = (
            previous_remaining <= ROUTE_COMPLETION_THRESHOLD_M
            or (
                previous_length > 0
                and (
                    previous_projection.along_route_m
                    / previous_length
                ) * 100.0 >= 99.0
            )
        )

    # --------------------------------------------------------
    # Persist stop lifecycle only during telemetry ingestion.
    # --------------------------------------------------------

    stops = RouteStopRepository(db).list_by_route(route_id)

    _evaluate_stop_lifecycle(
        db=db,
        route_stops=stops,
        current_latitude=current_state.latitude,
        current_longitude=current_state.longitude,
        route_points=points,
        vehicle_id=current_state.vehicle_id,
        sequence_number=current_state.sequence_number,
        mutate=True,
    )

    # --------------------------------------------------------
    # Route deviation transition.
    # --------------------------------------------------------

    if previous_status != result.deviation_status:

        if result.deviation_status == "DEVIATED":
            event = create_event(
                db=db,
                vehicle_id=current_state.vehicle_id,
                event_type=EVENT_ROUTE_DEVIATION,
                severity="warning",
                message=(
                    f"Vehicle is {result.distance_from_route_m:.1f} m "
                    f"from assigned route; threshold is "
                    f"{deviation_threshold_m:.1f} m."
                ),
                sequence_number=current_state.sequence_number,
            )

            process_event_for_alert(
                db=db,
                event=event,
            )

        elif previous_status == "DEVIATED":

            event = create_event(
                db=db,
                vehicle_id=current_state.vehicle_id,
                event_type=EVENT_ROUTE_DEVIATION_RECOVERED,
                severity="info",
                message=(
                    f"Vehicle returned within the assigned route "
                    f"deviation threshold ({deviation_threshold_m:.1f} m)."
                ),
                sequence_number=current_state.sequence_number,
            )

            process_event_for_alert(
                db=db,
                event=event,
            )

            from app.database.repositories.alert_repository import (
                AlertRepository,
            )

            alerts = AlertRepository(db).list_active_by_vehicle(
                current_state.vehicle_id,
            )

            for alert in alerts:
                if alert.alert_type == EVENT_ROUTE_DEVIATION:
                    AlertRepository(db).resolve(alert)

    # --------------------------------------------------------
    # Route completion transition.
    # --------------------------------------------------------

    if result.route_completed and not previous_completed:

        event = create_event(
            db=db,
            vehicle_id=current_state.vehicle_id,
            event_type=EVENT_ROUTE_COMPLETED,
            severity="info",
            message=(
                f"Vehicle completed assigned route {result.route_id}."
            ),
            sequence_number=current_state.sequence_number,
        )

        process_event_for_alert(
            db=db,
            event=event,
        )

    return result
