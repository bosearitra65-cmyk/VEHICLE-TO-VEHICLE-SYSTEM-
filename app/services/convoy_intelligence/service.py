from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from math import radians, sin, cos, asin, sqrt
from typing import Any

from sqlalchemy.orm import Session

from app.models.convoy import Convoy
from app.models.convoy_member import ConvoyMember
from app.models.vehicle_state import VehicleState


# ------------------------------------------------------------
# Configurable intelligence thresholds
# ------------------------------------------------------------

FRESH_SECONDS = 15
AGING_SECONDS = 30
STALE_SECONDS = 60

DEFAULT_SEPARATION_WARNING_M = 100.0


@dataclass
class VehicleConvoyIntelligence:
    vehicle_id: str
    role: str | None
    latitude: float | None
    longitude: float | None
    speed: float | None
    freshness_state: str
    communication_state: str | None

    distance_from_leader_m: float | None
    relative_speed_to_leader: float | None
    following_gap_m: float | None
    separation_status: str

    def to_dict(self):
        return asdict(self)


@dataclass
class ConvoyIntelligence:
    convoy_id: str
    leader_vehicle_id: str | None

    total_vehicle_count: int
    fresh_vehicle_count: int
    aging_vehicle_count: int
    stale_vehicle_count: int
    unavailable_vehicle_count: int

    convoy_spread_m: float
    minimum_vehicle_distance_m: float | None
    maximum_vehicle_distance_m: float | None

    separation_warning_count: int
    convoy_health: str

    vehicles: list[dict[str, Any]]

    def to_dict(self):
        return asdict(self)


def haversine_m(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:

    earth_radius_m = 6371000.0

    lat1 = radians(latitude_1)
    lat2 = radians(latitude_2)

    dlat = radians(latitude_2 - latitude_1)
    dlon = radians(longitude_2 - longitude_1)

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(dlon / 2) ** 2
    )

    return (
        2
        * earth_radius_m
        * asin(sqrt(a))
    )


def _state_timestamp(state):
    return (
        getattr(state, "received_at", None)
        or getattr(state, "updated_at", None)
        or getattr(state, "server_received_at", None)
    )


def _freshness_state(state) -> str:

    if state is None:
        return "UNAVAILABLE"

    timestamp = _state_timestamp(state)

    if timestamp is None:
        return "UNKNOWN"

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    age = (
        datetime.now(timezone.utc) - timestamp
    ).total_seconds()

    if age <= FRESH_SECONDS:
        return "FRESH"

    if age <= AGING_SECONDS:
        return "AGING"

    if age <= STALE_SECONDS:
        return "STALE"

    return "UNAVAILABLE"


def _speed(state):
    value = getattr(state, "speed", None)

    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _distance(
    a,
    b,
):
    if (
        a is None
        or b is None
        or a.latitude is None
        or a.longitude is None
        or b.latitude is None
        or b.longitude is None
    ):
        return None

    return haversine_m(
        float(a.latitude),
        float(a.longitude),
        float(b.latitude),
        float(b.longitude),
    )


def calculate_convoy_intelligence(
    db: Session,
    convoy_id: str,
    separation_warning_m: float = DEFAULT_SEPARATION_WARNING_M,
) -> ConvoyIntelligence:

    convoy = (
        db.query(Convoy)
        .filter(Convoy.convoy_id == convoy_id)
        .first()
    )

    if convoy is None:
        raise ValueError(
            f"Convoy not found: {convoy_id}"
        )

    members = (
        db.query(ConvoyMember)
        .filter(
            ConvoyMember.convoy_id == convoy_id,
            ConvoyMember.status == "active",
            ConvoyMember.left_at.is_(None),
        )
        .order_by(ConvoyMember.joined_at)
        .all()
    )

    state_by_vehicle = {}

    vehicle_ids = [
        member.vehicle_id
        for member in members
    ]

    if vehicle_ids:
        states = (
            db.query(VehicleState)
            .filter(
                VehicleState.vehicle_id.in_(vehicle_ids)
            )
            .all()
        )

        state_by_vehicle = {
            state.vehicle_id: state
            for state in states
        }

    leader_id = convoy.leader_vehicle_id

    # Fall back to the member explicitly marked as leader.
    if leader_id is None:
        for member in members:
            if str(member.role).upper() == "LEADER":
                leader_id = member.vehicle_id
                break

    leader_state = (
        state_by_vehicle.get(leader_id)
        if leader_id
        else None
    )

    results = []

    fresh = 0
    aging = 0
    stale = 0
    unavailable = 0
    separation_warnings = 0

    all_positions = []

    for member in members:

        state = state_by_vehicle.get(
            member.vehicle_id
        )

        freshness = _freshness_state(state)

        if freshness == "FRESH":
            fresh += 1
        elif freshness == "AGING":
            aging += 1
        elif freshness == "STALE":
            stale += 1
        elif freshness == "UNAVAILABLE":
            unavailable += 1

        distance_from_leader = None
        relative_speed = None
        following_gap = None
        separation_status = "UNKNOWN"

        if state is not None:
            if (
                state.latitude is not None
                and state.longitude is not None
            ):
                all_positions.append(
                    (
                        float(state.latitude),
                        float(state.longitude),
                    )
                )

        if (
            leader_state is not None
            and state is not None
        ):
            distance_from_leader = _distance(
                state,
                leader_state,
            )

            own_speed = _speed(state)
            leader_speed = _speed(leader_state)

            if (
                own_speed is not None
                and leader_speed is not None
            ):
                relative_speed = (
                    own_speed - leader_speed
                )

            # Following gap is the physical
            # leader-to-follower distance.
            if (
                str(member.role).upper() != "LEADER"
                and distance_from_leader is not None
            ):
                following_gap = distance_from_leader

                if (
                    following_gap
                    > separation_warning_m
                ):
                    separation_status = "WARNING"
                    separation_warnings += 1
                else:
                    separation_status = "NORMAL"

        results.append(
            VehicleConvoyIntelligence(
                vehicle_id=member.vehicle_id,
                role=member.role,
                latitude=(
                    float(state.latitude)
                    if state is not None
                    and state.latitude is not None
                    else None
                ),
                longitude=(
                    float(state.longitude)
                    if state is not None
                    and state.longitude is not None
                    else None
                ),
                speed=_speed(state),
                freshness_state=freshness,
                communication_state=(
                    getattr(
                        state,
                        "communication_status",
                        None,
                    )
                    if state is not None
                    else None
                ),
                distance_from_leader_m=distance_from_leader,
                relative_speed_to_leader=relative_speed,
                following_gap_m=following_gap,
                separation_status=separation_status,
            ).to_dict()
        )

    # --------------------------------------------------------
    # Convoy spread
    #
    # Maximum pairwise distance between available
    # vehicle positions.
    # --------------------------------------------------------

    pairwise_distances = []

    for i in range(len(all_positions)):
        for j in range(i + 1, len(all_positions)):
            a = all_positions[i]
            b = all_positions[j]

            pairwise_distances.append(
                haversine_m(
                    a[0],
                    a[1],
                    b[0],
                    b[1],
                )
            )

    convoy_spread = (
        max(pairwise_distances)
        if pairwise_distances
        else 0.0
    )

    minimum_distance = (
        min(pairwise_distances)
        if pairwise_distances
        else None
    )

    maximum_distance = (
        max(pairwise_distances)
        if pairwise_distances
        else None
    )

    if unavailable > 0:
        convoy_health = "DEGRADED"
    elif separation_warnings > 0:
        convoy_health = "SEPARATION_WARNING"
    elif stale > 0:
        convoy_health = "DEGRADED"
    elif aging > 0:
        convoy_health = "AGING"
    elif fresh == len(members) and members:
        convoy_health = "HEALTHY"
    else:
        convoy_health = "UNKNOWN"

    return ConvoyIntelligence(
        convoy_id=convoy_id,
        leader_vehicle_id=leader_id,
        total_vehicle_count=len(members),
        fresh_vehicle_count=fresh,
        aging_vehicle_count=aging,
        stale_vehicle_count=stale,
        unavailable_vehicle_count=unavailable,
        convoy_spread_m=convoy_spread,
        minimum_vehicle_distance_m=minimum_distance,
        maximum_vehicle_distance_m=maximum_distance,
        separation_warning_count=separation_warnings,
        convoy_health=convoy_health,
        vehicles=results,
    )


def calculate_vehicle_pair_distance(
    db: Session,
    vehicle_a_id: str,
    vehicle_b_id: str,
):
    states = (
        db.query(VehicleState)
        .filter(
            VehicleState.vehicle_id.in_(
                [vehicle_a_id, vehicle_b_id]
            )
        )
        .all()
    )

    state_map = {
        state.vehicle_id: state
        for state in states
    }

    a = state_map.get(vehicle_a_id)
    b = state_map.get(vehicle_b_id)

    if a is None or b is None:
        return {
            "vehicle_a": vehicle_a_id,
            "vehicle_b": vehicle_b_id,
            "distance_m": None,
            "status": "UNAVAILABLE",
        }

    distance = _distance(a, b)

    return {
        "vehicle_a": vehicle_a_id,
        "vehicle_b": vehicle_b_id,
        "distance_m": distance,
        "status": (
            "AVAILABLE"
            if distance is not None
            else "UNAVAILABLE"
        ),
    }
