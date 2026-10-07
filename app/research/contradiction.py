
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


CONTRADICTION_TYPES = {
    "TEMPORAL",
    "SPATIAL",
    "MOTION",
    "ROUTE",
    "CONVOY",
}

SEVERITIES = {
    "NONE",
    "LOW",
    "MEDIUM",
    "HIGH",
}


@dataclass(frozen=True)
class ContradictionThreshold:
    low: float
    medium: float
    high: float

    def __post_init__(self) -> None:
        if not (
            0.0 <= self.low
            <= self.medium
            <= self.high
        ):
            raise ValueError(
                "Thresholds must satisfy "
                "0 <= low <= medium <= high"
            )


DEFAULT_THRESHOLDS = {
    "TEMPORAL": ContradictionThreshold(
        low=2.0,
        medium=5.0,
        high=15.0,
    ),
    "SPATIAL": ContradictionThreshold(
        low=25.0,
        medium=100.0,
        high=500.0,
    ),
    "MOTION": ContradictionThreshold(
        low=5.0,
        medium=15.0,
        high=40.0,
    ),
    "ROUTE": ContradictionThreshold(
        low=50.0,
        medium=200.0,
        high=1000.0,
    ),
    "CONVOY": ContradictionThreshold(
        low=50.0,
        medium=200.0,
        high=1000.0,
    ),
}


@dataclass(frozen=True)
class ContradictionRecord:
    contradiction_id: str
    contradiction_type: str
    evidence_a: float
    evidence_b: float
    difference: float
    threshold_used: float
    severity: str
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        timestamp = self.timestamp

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(
                tzinfo=timezone.utc
            )
        else:
            timestamp = timestamp.astimezone(
                timezone.utc
            )

        return {
            "contradiction_id": self.contradiction_id,
            "contradiction_type":
                self.contradiction_type,
            "evidence_a": self.evidence_a,
            "evidence_b": self.evidence_b,
            "difference": self.difference,
            "threshold_used":
                self.threshold_used,
            "severity": self.severity,
            "timestamp":
                timestamp.isoformat(),
        }


def classify_severity(
    difference: float,
    threshold: ContradictionThreshold,
) -> str:
    difference = abs(float(difference))

    if difference < threshold.low:
        return "NONE"

    if difference < threshold.medium:
        return "LOW"

    if difference < threshold.high:
        return "MEDIUM"

    return "HIGH"


def detect_contradiction(
    contradiction_id: str,
    contradiction_type: str,
    evidence_a: float,
    evidence_b: float,
    timestamp: datetime,
    threshold: ContradictionThreshold | None = None,
) -> ContradictionRecord:
    contradiction_type = contradiction_type.upper()

    if contradiction_type not in CONTRADICTION_TYPES:
        raise ValueError(
            f"Unsupported contradiction type: "
            f"{contradiction_type}"
        )

    effective_threshold = (
        threshold
        if threshold is not None
        else DEFAULT_THRESHOLDS[contradiction_type]
    )

    difference = abs(
        float(evidence_a) - float(evidence_b)
    )

    severity = classify_severity(
        difference,
        effective_threshold,
    )

    return ContradictionRecord(
        contradiction_id=contradiction_id,
        contradiction_type=contradiction_type,
        evidence_a=float(evidence_a),
        evidence_b=float(evidence_b),
        difference=difference,
        threshold_used=effective_threshold.high,
        severity=severity,
        timestamp=timestamp,
    )


def detect_all(
    observations: dict[str, tuple[float, float]],
    timestamp: datetime,
) -> list[ContradictionRecord]:
    """
    Evaluate independent evidence pairs.

    Input:
        {
            "TEMPORAL": (value_a, value_b),
            ...
        }

    This function detects inconsistency only.
    It does not classify a vehicle as faulty and does not
    modify any authoritative vehicle state.
    """
    results = []

    for contradiction_type, values in observations.items():
        contradiction_type = contradiction_type.upper()

        if contradiction_type not in CONTRADICTION_TYPES:
            raise ValueError(
                f"Unsupported contradiction type: "
                f"{contradiction_type}"
            )

        if len(values) != 2:
            raise ValueError(
                "Each contradiction observation "
                "must contain exactly two values"
            )

        results.append(
            detect_contradiction(
                contradiction_id=(
                    f"CONTR-{contradiction_type}"
                ),
                contradiction_type=contradiction_type,
                evidence_a=values[0],
                evidence_b=values[1],
                timestamp=timestamp,
            )
        )

    return results
