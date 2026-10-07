from pathlib import Path

research_dir = Path("app/research")
research_dir.mkdir(parents=True, exist_ok=True)

module = r'''
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
'''

test = r'''
from datetime import datetime, timezone

from app.research.contradiction import (
    ContradictionThreshold,
    detect_all,
    detect_contradiction,
)


NOW = datetime(
    2026,
    1,
    1,
    12,
    0,
    0,
    tzinfo=timezone.utc,
)


def test_no_contradiction():
    result = detect_contradiction(
        contradiction_id="TEST-NONE",
        contradiction_type="TEMPORAL",
        evidence_a=10.0,
        evidence_b=11.0,
        timestamp=NOW,
    )

    assert result.difference == 1.0
    assert result.severity == "NONE"

    print("NO_CONTRADICTION=PASS")


def test_low():
    threshold = ContradictionThreshold(
        low=2.0,
        medium=5.0,
        high=15.0,
    )

    result = detect_contradiction(
        contradiction_id="TEST-LOW",
        contradiction_type="TEMPORAL",
        evidence_a=10.0,
        evidence_b=13.0,
        timestamp=NOW,
        threshold=threshold,
    )

    assert abs(result.difference - 3.0) < 1e-9
    assert result.severity == "LOW"

    print("LOW_CONTRADICTION=PASS")


def test_medium():
    result = detect_contradiction(
        contradiction_id="TEST-MEDIUM",
        contradiction_type="SPATIAL",
        evidence_a=100.0,
        evidence_b=250.0,
        timestamp=NOW,
    )

    assert abs(result.difference - 150.0) < 1e-9
    assert result.severity == "MEDIUM"

    print("MEDIUM_CONTRADICTION=PASS")


def test_high():
    result = detect_contradiction(
        contradiction_id="TEST-HIGH",
        contradiction_type="MOTION",
        evidence_a=0.0,
        evidence_b=50.0,
        timestamp=NOW,
    )

    assert abs(result.difference - 50.0) < 1e-9
    assert result.severity == "HIGH"

    print("HIGH_CONTRADICTION=PASS")


def test_structured_record():
    result = detect_contradiction(
        contradiction_id="TEST-RECORD",
        contradiction_type="ROUTE",
        evidence_a=100.0,
        evidence_b=350.0,
        timestamp=NOW,
    )

    data = result.to_dict()

    required = {
        "contradiction_id",
        "contradiction_type",
        "evidence_a",
        "evidence_b",
        "difference",
        "threshold_used",
        "severity",
        "timestamp",
    }

    assert required.issubset(data)
    assert data["contradiction_type"] == "ROUTE"
    assert data["severity"] == "MEDIUM"

    print("STRUCTURED_RECORD=PASS")


def test_all_dimensions():
    results = detect_all(
        {
            "TEMPORAL": (10.0, 20.0),
            "SPATIAL": (100.0, 150.0),
            "MOTION": (20.0, 80.0),
            "ROUTE": (100.0, 400.0),
            "CONVOY": (100.0, 1200.0),
        },
        NOW,
    )

    assert len(results) == 5

    types = {
        result.contradiction_type
        for result in results
    }

    assert types == {
        "TEMPORAL",
        "SPATIAL",
        "MOTION",
        "ROUTE",
        "CONVOY",
    }

    print("ALL_FIVE_DIMENSIONS=PASS")


def test_invalid_type():
    try:
        detect_contradiction(
            contradiction_id="TEST-INVALID",
            contradiction_type="UNKNOWN",
            evidence_a=1.0,
            evidence_b=2.0,
            timestamp=NOW,
        )
    except ValueError:
        print("INVALID_TYPE_VALIDATION=PASS")
        return

    raise AssertionError(
        "Unsupported contradiction type was accepted"
    )


test_no_contradiction()
test_low()
test_medium()
test_high()
test_structured_record()
test_all_dimensions()
test_invalid_type()

print("CONTRADICTION_LAYER_V0=PASS")
'''

(research_dir / "contradiction.py").write_text(
    module,
    encoding="utf-8",
)

Path("stage10_step5_2_verify.py").write_text(
    test,
    encoding="utf-8",
)

print("=" * 70)
print("STAGE 10 - STEP 5.2")
print("CRITICAL-EVIDENCE CONTRADICTION LAYER CREATED")
print("=" * 70)
print("MODULE=app/research/contradiction.py")
print("DIMENSIONS=5")
print("SEVERITIES=NONE/LOW/MEDIUM/HIGH")
print("STRUCTURED_EVIDENCE=IMPLEMENTED")
print("CANDIDATE_STATE_CHANGE=NOT_IMPLEMENTED")
print("PRODUCTION_STATE_MODIFIED=NO")
print("DATABASE_MODIFIED=NO")
print("MIGRATION_CREATED=NO")
print("=" * 70)
