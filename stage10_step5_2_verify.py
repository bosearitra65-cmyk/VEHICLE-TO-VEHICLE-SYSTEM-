
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
