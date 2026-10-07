
from app.research.candidate_reliability import (
    classify_reliability,
    evaluate_reliability,
)


NORMAL = {
    "temporal": 1.0,
    "spatial": 1.0,
    "motion": 1.0,
    "route": 1.0,
    "communication": 1.0,
    "convoy": 1.0,
}


def test_normal():
    result = evaluate_reliability(NORMAL)

    assert result.score == 1.0
    assert result.state == "NORMAL"

    print("NORMAL_STATE=PASS")


def test_degraded():
    evidence = {
        "temporal": 0.5,
        "spatial": 0.5,
        "motion": 0.5,
        "route": 1.0,
        "communication": 1.0,
        "convoy": 1.0,
    }

    result = evaluate_reliability(evidence)

    assert abs(result.score - 0.75) < 1e-9
    assert result.state == "DEGRADED"

    print("DEGRADED_STATE=PASS")


def test_suspect():
    evidence = {
        "temporal": 0.5,
        "spatial": 0.5,
        "motion": 0.5,
        "route": 0.5,
        "communication": 0.5,
        "convoy": 0.5,
    }

    result = evaluate_reliability(evidence)

    assert abs(result.score - 0.5) < 1e-9
    assert result.state == "SUSPECT"

    print("SUSPECT_STATE=PASS")


def test_untrusted():
    evidence = {
        "temporal": 0.1,
        "spatial": 0.1,
        "motion": 0.1,
        "route": 0.1,
        "communication": 0.1,
        "convoy": 0.1,
    }

    result = evaluate_reliability(evidence)

    assert abs(result.score - 0.1) < 1e-9
    assert result.state == "UNTRUSTED"

    print("UNTRUSTED_STATE=PASS")


def test_weighting():
    evidence = dict(NORMAL)
    evidence["communication"] = 0.0

    weights = {
        "temporal": 0.0,
        "spatial": 0.0,
        "motion": 0.0,
        "route": 0.0,
        "communication": 1.0,
        "convoy": 0.0,
    }

    result = evaluate_reliability(
        evidence,
        weights=weights,
    )

    assert abs(result.score - 0.0) < 1e-9
    assert result.state == "UNTRUSTED"

    print("WEIGHTED_EVALUATION=PASS")


def test_threshold_validation():
    try:
        classify_reliability(
            0.5,
            {
                "normal": 0.5,
                "degraded": 0.7,
                "suspect": 0.2,
            },
        )
    except ValueError:
        print("THRESHOLD_VALIDATION=PASS")
        return

    raise AssertionError(
        "Invalid thresholds were accepted"
    )


test_normal()
test_degraded()
test_suspect()
test_untrusted()
test_weighting()
test_threshold_validation()

print("CANDIDATE_RELIABILITY_V0=PASS")
