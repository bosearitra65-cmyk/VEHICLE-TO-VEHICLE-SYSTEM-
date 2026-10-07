from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.convoy import Convoy
from app.models.convoy_member import ConvoyMember
from app.models.journey import Journey
from app.models.route import Route
from app.models.vehicle_state import VehicleState
from app.services.convoy_intelligence.service import calculate_convoy_intelligence
from app.services.route_progress.service import calculate_route_progress


@dataclass(frozen=True)
class VehicleOperationalIntelligence:
    vehicle_id: str
    route_id: str
    journey_id: str | None
    progress_percent: float
    distance_travelled_m: float
    distance_remaining_m: float
    distance_from_route_m: float
    deviation_status: str
    route_completed: bool
    current_stop_id: str | None
    current_stop_name: str | None
    next_stop_id: str | None
    next_stop_name: str | None
    speed_mps: float
    eta_seconds: float | None
    eta_status: str
    eta_confidence: str
    traffic_available: bool
    traffic_status: str
    reroute_recommended: bool
    reroute_reason: str | None
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "vehicle_id": self.vehicle_id,
            "route_id": self.route_id,
            "journey_id": self.journey_id,
            "progress_percent": self.progress_percent,
            "distance_travelled_m": self.distance_travelled_m,
            "distance_remaining_m": self.distance_remaining_m,
            "distance_from_route_m": self.distance_from_route_m,
            "deviation_status": self.deviation_status,
            "route_completed": self.route_completed,
            "current_stop_id": self.current_stop_id,
            "current_stop_name": self.current_stop_name,
            "next_stop_id": self.next_stop_id,
            "next_stop_name": self.next_stop_name,
            "speed_mps": self.speed_mps,
            "eta_seconds": self.eta_seconds,
            "eta_status": self.eta_status,
            "eta_confidence": self.eta_confidence,
            "traffic_available": self.traffic_available,
            "traffic_status": self.traffic_status,
            "reroute_recommended": self.reroute_recommended,
            "reroute_reason": self.reroute_reason,
            "generated_at": self.generated_at,
        }


@dataclass(frozen=True)
class ConvoyOperationalIntelligence:
    convoy_id: str
    journey_id: str | None
    route_id: str | None
    journey_status: str | None
    route_status: str
    total_vehicle_count: int
    operational_vehicle_count: int
    unavailable_vehicle_count: int
    average_progress_percent: float | None
    leader_progress_percent: float | None
    convoy_distance_remaining_m: float | None
    convoy_eta_seconds: float | None
    eta_status: str
    eta_confidence: str
    convoy_health: str
    separation_warning_count: int
    reroute_recommended: bool
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "convoy_id": self.convoy_id,
            "journey_id": self.journey_id,
            "route_id": self.route_id,
            "journey_status": self.journey_status,
            "route_status": self.route_status,
            "total_vehicle_count": self.total_vehicle_count,
            "operational_vehicle_count": self.operational_vehicle_count,
            "unavailable_vehicle_count": self.unavailable_vehicle_count,
            "average_progress_percent": self.average_progress_percent,
            "leader_progress_percent": self.leader_progress_percent,
            "convoy_distance_remaining_m": self.convoy_distance_remaining_m,
            "convoy_eta_seconds": self.convoy_eta_seconds,
            "eta_status": self.eta_status,
            "eta_confidence": self.eta_confidence,
            "convoy_health": self.convoy_health,
            "separation_warning_count": self.separation_warning_count,
            "reroute_recommended": self.reroute_recommended,
            "generated_at": self.generated_at,
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _eta_from_state(
    distance_remaining_m: float,
    speed_mps: float,
) -> tuple[float | None, str, str]:
    if distance_remaining_m <= 0:
        return 0.0, "ARRIVED", "HIGH"

    if speed_mps <= 0:
        return None, "NO_MOVEMENT", "LOW"

    eta = distance_remaining_m / speed_mps

    if speed_mps < 2:
        confidence = "LOW"
    elif speed_mps < 8:
        confidence = "MEDIUM"
    else:
        confidence = "HIGH"

    return eta, "BASELINE", confidence


def _journey_for_vehicle(
    db: Session,
    vehicle_id: str,
) -> Journey | None:
    membership = (
        db.query(ConvoyMember)
        .filter(
            ConvoyMember.vehicle_id == vehicle_id,
            ConvoyMember.left_at.is_(None),
        )
        .first()
    )

    if membership is None:
        return None

    convoy = (
        db.query(Convoy)
        .filter(Convoy.convoy_id == membership.convoy_id)
        .first()
    )

    if convoy is None or convoy.journey_id is None:
        return None

    return (
        db.query(Journey)
        .filter(Journey.journey_id == convoy.journey_id)
        .first()
    )


def calculate_vehicle_operational_intelligence(
    db: Session,
    vehicle_id: str,
    route_id: str | None = None,
    deviation_threshold_m: float = 100.0,
) -> VehicleOperationalIntelligence:

    state = (
        db.query(VehicleState)
        .filter(VehicleState.vehicle_id == vehicle_id)
        .first()
    )

    if state is None:
        raise ValueError(f"Vehicle state not found: {vehicle_id}")

    journey = _journey_for_vehicle(db, vehicle_id)

    if route_id is None:
        route_id = journey.route_id if journey else None

    if route_id is None:
        raise ValueError(
            f"No route is assigned to vehicle {vehicle_id}"
        )

    route = (
        db.query(Route)
        .filter(Route.route_id == route_id)
        .first()
    )

    if route is None:
        raise ValueError(f"Route not found: {route_id}")

    progress = calculate_route_progress(
        db=db,
        vehicle_id=vehicle_id,
        route_id=route_id,
        deviation_threshold_m=deviation_threshold_m,
    )

    speed_mps = float(state.speed or 0.0)

    eta_seconds, eta_status, eta_confidence = _eta_from_state(
        progress.distance_remaining_m,
        speed_mps,
    )

    reroute_recommended = (
        progress.deviation_status == "DEVIATED"
        and not progress.route_completed
    )

    reroute_reason = (
        "Vehicle is outside the configured route deviation threshold."
        if reroute_recommended
        else None
    )

    if progress.route_completed:
        eta_status = "ARRIVED"
        eta_confidence = "HIGH"

    return VehicleOperationalIntelligence(
        vehicle_id=vehicle_id,
        route_id=route_id,
        journey_id=journey.journey_id if journey else None,
        progress_percent=progress.progress_percent,
        distance_travelled_m=progress.distance_travelled_m,
        distance_remaining_m=progress.distance_remaining_m,
        distance_from_route_m=progress.distance_from_route_m,
        deviation_status=progress.deviation_status,
        route_completed=progress.route_completed,
        current_stop_id=progress.current_stop_id,
        current_stop_name=progress.current_stop_name,
        next_stop_id=progress.next_stop_id,
        next_stop_name=progress.next_stop_name,
        speed_mps=speed_mps,
        eta_seconds=eta_seconds,
        eta_status=eta_status,
        eta_confidence=eta_confidence,
        traffic_available=False,
        traffic_status="TRAFFIC_UNAVAILABLE",
        reroute_recommended=reroute_recommended,
        reroute_reason=reroute_reason,
        generated_at=_utc_now(),
    )


def calculate_convoy_operational_intelligence(
    db: Session,
    convoy_id: str,
    deviation_threshold_m: float = 100.0,
) -> ConvoyOperationalIntelligence:

    convoy = (
        db.query(Convoy)
        .filter(Convoy.convoy_id == convoy_id)
        .first()
    )

    if convoy is None:
        raise ValueError(f"Convoy not found: {convoy_id}")

    members = (
        db.query(ConvoyMember)
        .filter(
            ConvoyMember.convoy_id == convoy_id,
            ConvoyMember.left_at.is_(None),
        )
        .all()
    )

    journey = None

    if convoy.journey_id:
        journey = (
            db.query(Journey)
            .filter(Journey.journey_id == convoy.journey_id)
            .first()
        )

    route_id = convoy.route_id

    if route_id is None and journey is not None:
        route_id = journey.route_id

    results: list[VehicleOperationalIntelligence] = []

    for member in members:
        try:
            results.append(
                calculate_vehicle_operational_intelligence(
                    db=db,
                    vehicle_id=member.vehicle_id,
                    deviation_threshold_m=deviation_threshold_m,
                )
            )
        except ValueError:
            continue

    convoy_base = calculate_convoy_intelligence(
        db=db,
        convoy_id=convoy_id,
        separation_warning_m=100.0,
    )

    progress_values = [
        item.progress_percent
        for item in results
        if item.progress_percent is not None
    ]

    remaining_values = [
        item.distance_remaining_m
        for item in results
        if item.distance_remaining_m is not None
    ]

    eta_values = [
        item.eta_seconds
        for item in results
        if item.eta_seconds is not None
    ]

    leader_progress = next(
        (
            item.progress_percent
            for item in results
            if item.vehicle_id == convoy.leader_vehicle_id
        ),
        None,
    )

    average_progress = (
        sum(progress_values) / len(progress_values)
        if progress_values
        else None
    )

    convoy_remaining = (
        max(remaining_values)
        if remaining_values
        else None
    )

    convoy_eta = (
        max(eta_values)
        if eta_values
        else None
    )

    reroute = any(
        item.reroute_recommended
        for item in results
    )

    if reroute:
        route_status = "DEVIATION_REQUIRES_REVIEW"
    elif results and all(
        item.route_completed
        for item in results
    ):
        route_status = "COMPLETED"
    elif results:
        route_status = "ACTIVE"
    else:
        route_status = "UNAVAILABLE"

    if convoy_eta is None:
        eta_status = "UNAVAILABLE"
        eta_confidence = "LOW"
    else:
        eta_status = "BASELINE"
        eta_confidence = (
            "HIGH"
            if len(eta_values) == len(results) and results
            else "MEDIUM"
        )

    return ConvoyOperationalIntelligence(
        convoy_id=convoy_id,
        journey_id=journey.journey_id if journey else None,
        route_id=route_id,
        journey_status=journey.status if journey else None,
        route_status=route_status,
        total_vehicle_count=convoy_base.total_vehicle_count,
        operational_vehicle_count=len(results),
        unavailable_vehicle_count=(
            convoy_base.total_vehicle_count - len(results)
        ),
        average_progress_percent=average_progress,
        leader_progress_percent=leader_progress,
        convoy_distance_remaining_m=convoy_remaining,
        convoy_eta_seconds=convoy_eta,
        eta_status=eta_status,
        eta_confidence=eta_confidence,
        convoy_health=convoy_base.convoy_health,
        separation_warning_count=convoy_base.separation_warning_count,
        reroute_recommended=reroute,
        generated_at=_utc_now(),
    )


def calculate_journey_operational_intelligence(
    db: Session,
    journey_id: str,
    deviation_threshold_m: float = 100.0,
) -> dict[str, Any]:

    journey = (
        db.query(Journey)
        .filter(Journey.journey_id == journey_id)
        .first()
    )

    if journey is None:
        raise ValueError(f"Journey not found: {journey_id}")

    convoy = (
        db.query(Convoy)
        .filter(Convoy.convoy_id == journey.convoy_id)
        .first()
    )

    if convoy is None:
        raise ValueError(
            f"Convoy not found: {journey.convoy_id}"
        )

    operational = calculate_convoy_operational_intelligence(
        db=db,
        convoy_id=convoy.convoy_id,
        deviation_threshold_m=deviation_threshold_m,
    )

    return {
        "journey_id": journey.journey_id,
        "journey_status": journey.status,
        "origin": journey.origin,
        "destination": journey.destination,
        "planned_start_at": (
            journey.planned_start_at.isoformat()
            if journey.planned_start_at
            else None
        ),
        "actual_start_at": (
            journey.actual_start_at.isoformat()
            if journey.actual_start_at
            else None
        ),
        "completed_at": (
            journey.completed_at.isoformat()
            if journey.completed_at
            else None
        ),
        "convoy_id": journey.convoy_id,
        "route_id": journey.route_id,
        "operational": operational.to_dict(),
        "generated_at": _utc_now(),
    }
