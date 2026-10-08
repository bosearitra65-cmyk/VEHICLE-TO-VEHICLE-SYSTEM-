from __future__ import annotations

import math

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.research.candidate_reliability import (
    ReliabilityResult,
    evaluate_reliability,
)
from app.research.contradiction import (
    ContradictionRecord,
    detect_contradiction,
)


EARTH_RADIUS_M = 6_371_000.0

# These are explicit research defaults, not production claims.
# They are intentionally configurable and can be changed during later
# experiment design without changing the authoritative vehicle model.
DEFAULT_CONFIG = {
    "max_temporal_gap_s": 120.0,
    "spatial_tolerance_m": 100.0,
    "motion_tolerance_ratio": 0.25,
}


@dataclass(frozen=True)
class VehicleEvidenceResult:
    vehicle_id: str
    sequence_number: int
    timestamp: datetime
    evidence: dict[str, float]
    reliability: ReliabilityResult
    contradictions: tuple[ContradictionRecord, ...]
    read_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "vehicle_id": self.vehicle_id,
            "sequence_number": self.sequence_number,
            "timestamp": self.timestamp.isoformat(),
            "evidence": dict(self.evidence),
            "reliability": self.reliability.to_dict(),
            "contradictions": [
                item.to_dict() for item in self.contradictions
            ],
            "read_only": self.read_only,
        }


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _haversine_m(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = (
        math.sin(dp / 2.0) ** 2
        + math.cos(p1)
        * math.cos(p2)
        * math.sin(dl / 2.0) ** 2
    )

    return 2.0 * EARTH_RADIUS_M * math.asin(
        min(1.0, math.sqrt(a))
    )


def _temporal_evidence(
    current_timestamp: datetime,
    previous_timestamp: datetime | None,
    max_gap_s: float,
) -> tuple[float, float | None]:
    if previous_timestamp is None:
        return 1.0, None

    if current_timestamp.tzinfo is None:
        current_timestamp = current_timestamp.replace(tzinfo=timezone.utc)
    else:
        current_timestamp = current_timestamp.astimezone(timezone.utc)

    if previous_timestamp.tzinfo is None:
        previous_timestamp = previous_timestamp.replace(tzinfo=timezone.utc)
    else:
        previous_timestamp = previous_timestamp.astimezone(timezone.utc)

    gap = (
        current_timestamp - previous_timestamp
    ).total_seconds()

    if gap < 0:
        return 0.0, gap

    if gap <= max_gap_s:
        return 1.0, gap

    return _clamp(1.0 - ((gap - max_gap_s) / max_gap_s)), gap


def _spatial_evidence(
    current_latitude: float,
    current_longitude: float,
    previous_latitude: float | None,
    previous_longitude: float | None,
    elapsed_s: float | None,
    current_speed: float,
    previous_speed: float | None,
    tolerance_m: float,
) -> tuple[float, float | None]:
    if (
        previous_latitude is None
        or previous_longitude is None
        or elapsed_s is None
        or elapsed_s <= 0
    ):
        return 1.0, None

    displacement_m = _haversine_m(
        previous_latitude,
        previous_longitude,
        current_latitude,
        current_longitude,
    )

    reference_speed = max(
        0.0,
        current_speed,
        previous_speed or 0.0,
    )

    expected_m = reference_speed * elapsed_s + tolerance_m

    if displacement_m <= expected_m:
        return 1.0, displacement_m

    excess = displacement_m - expected_m
    return _clamp(1.0 - (excess / max(expected_m, tolerance_m))), displacement_m


def _motion_evidence(
    current_speed: float,
    previous_speed: float | None,
    displacement_m: float | None,
    elapsed_s: float | None,
    tolerance_ratio: float,
) -> tuple[float, float | None]:
    if (
        displacement_m is None
        or elapsed_s is None
        or elapsed_s <= 0
    ):
        return 1.0, None

    implied_speed = displacement_m / elapsed_s
    reported_speed = max(0.0, float(current_speed))

    denominator = max(
        reported_speed,
        implied_speed,
        1.0,
    )

    relative_error = abs(
        reported_speed - implied_speed
    ) / denominator

    if relative_error <= tolerance_ratio:
        return 1.0, relative_error

    excess = relative_error - tolerance_ratio
    return _clamp(
        1.0 - (excess / max(tolerance_ratio, 0.01)),
    ), relative_error


def _route_evidence(route_result: Any) -> float:
    if route_result is None:
        # No route evidence is available; do not treat absence of a route
        # as a route failure.
        return 0.5

    status = str(
        getattr(route_result, "deviation_status", "")
    ).upper()

    if status == "DEVIATED":
        return 0.0

    if status == "NORMAL":
        return 1.0

    return 0.5


def _communication_evidence(
    communication_status: Any,
    availability: Any,
) -> float:
    values = {
        str(communication_status or "").upper(),
        str(availability or "").upper(),
    }

    if values & {
        "DISCONNECTED",
        "UNAVAILABLE",
        "OFFLINE",
    }:
        return 0.0

    if values & {
        "RECONNECTING",
        "FALLBACK",
    }:
        return 0.5

    if values & {
        "LIVE",
        "CONNECTED",
        "AVAILABLE",
        "FRESH",
    }:
        return 1.0

    return 0.5


def _convoy_evidence(
    convoy_id: Any,
    role: Any,
) -> float:
    if not convoy_id:
        return 0.5

    if role and str(role).upper() in {
        "LEADER",
        "FOLLOWER",
    }:
        return 1.0

    return 0.5


def evaluate_vehicle_evidence(
    *,
    current_state: Any,
    previous_timestamp: datetime | None = None,
    previous_latitude: float | None = None,
    previous_longitude: float | None = None,
    previous_speed: float | None = None,
    availability: Any = None,
    route_result: Any = None,
    config: dict[str, float] | None = None,
) -> VehicleEvidenceResult:
    """
    Read-only Step 10.5.3 adapter.

    It consumes an already accepted authoritative VehicleState plus
    already-computed operational context. It performs no database writes,
    commits, model mutation, event creation, alert creation, or realtime
    publication.
    """
    cfg = dict(DEFAULT_CONFIG)
    if config:
        cfg.update(config)

    temporal, temporal_gap = _temporal_evidence(
        current_state.timestamp,
        previous_timestamp,
        float(cfg["max_temporal_gap_s"]),
    )

    elapsed_s = (
        temporal_gap
        if temporal_gap is not None
        else None
    )

    spatial, displacement_m = _spatial_evidence(
        current_state.latitude,
        current_state.longitude,
        previous_latitude,
        previous_longitude,
        elapsed_s,
        current_state.speed,
        previous_speed,
        float(cfg["spatial_tolerance_m"]),
    )

    motion, relative_motion_error = _motion_evidence(
        current_state.speed,
        previous_speed,
        displacement_m,
        elapsed_s,
        float(cfg["motion_tolerance_ratio"]),
    )

    route = _route_evidence(route_result)

    communication = _communication_evidence(
        current_state.communication_status,
        availability,
    )

    convoy = _convoy_evidence(
        current_state.convoy_id,
        current_state.role,
    )

    evidence = {
        "temporal": _clamp(temporal),
        "spatial": _clamp(spatial),
        "motion": _clamp(motion),
        "route": _clamp(route),
        "communication": _clamp(communication),
        "convoy": _clamp(convoy),
    }

    reliability = evaluate_reliability(evidence)

    contradictions: list[ContradictionRecord] = []

    if temporal_gap is not None:
        contradictions.append(
            detect_contradiction(
                contradiction_id=(
                    f"{current_state.vehicle_id}:"
                    f"{current_state.sequence_number}:TEMPORAL"
                ),
                contradiction_type="TEMPORAL",
                evidence_a=temporal_gap,
                evidence_b=0.0,
                timestamp=current_state.timestamp,
            )
        )

    if displacement_m is not None:
        contradictions.append(
            detect_contradiction(
                contradiction_id=(
                    f"{current_state.vehicle_id}:"
                    f"{current_state.sequence_number}:SPATIAL"
                ),
                contradiction_type="SPATIAL",
                evidence_a=displacement_m,
                evidence_b=0.0,
                timestamp=current_state.timestamp,
            )
        )

    if relative_motion_error is not None:
        # The contradiction engine expects domain-scale values.
        # Convert the relative error into a percentage for its motion
        # thresholds, without altering authoritative state.
        motion_difference = relative_motion_error * 100.0

        contradictions.append(
            detect_contradiction(
                contradiction_id=(
                    f"{current_state.vehicle_id}:"
                    f"{current_state.sequence_number}:MOTION"
                ),
                contradiction_type="MOTION",
                evidence_a=motion_difference,
                evidence_b=0.0,
                timestamp=current_state.timestamp,
            )
        )

    if route_result is not None:
        distance_from_route = float(
            getattr(
                route_result,
                "distance_from_route_m",
                0.0,
            )
        )

        contradictions.append(
            detect_contradiction(
                contradiction_id=(
                    f"{current_state.vehicle_id}:"
                    f"{current_state.sequence_number}:ROUTE"
                ),
                contradiction_type="ROUTE",
                evidence_a=distance_from_route,
                evidence_b=0.0,
                timestamp=current_state.timestamp,
            )
        )

    return VehicleEvidenceResult(
        vehicle_id=current_state.vehicle_id,
        sequence_number=current_state.sequence_number,
        timestamp=current_state.timestamp,
        evidence=evidence,
        reliability=reliability,
        contradictions=tuple(contradictions),
        read_only=True,
    )
