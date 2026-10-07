from pathlib import Path

research_dir = Path("app/research")
research_dir.mkdir(parents=True, exist_ok=True)

module = r'''
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DEFAULT_WEIGHTS = {
    "temporal": 1.0,
    "spatial": 1.0,
    "motion": 1.0,
    "route": 1.0,
    "communication": 1.0,
    "convoy": 1.0,
}


DEFAULT_THRESHOLDS = {
    "normal": 0.80,
    "degraded": 0.60,
    "suspect": 0.40,
}


@dataclass(frozen=True)
class ReliabilityResult:
    score: float
    state: str
    evidence: dict[str, float]
    weights: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "state": self.state,
            "evidence": dict(self.evidence),
            "weights": dict(self.weights),
        }


def _validate_evidence(
    evidence: dict[str, float],
) -> dict[str, float]:
    required = set(DEFAULT_WEIGHTS)

    missing = required - set(evidence)

    if missing:
        raise ValueError(
            "Missing evidence: "
            + ", ".join(sorted(missing))
        )

    normalized = {}

    for name in required:
        value = float(evidence[name])

        if not 0.0 <= value <= 1.0:
            raise ValueError(
                f"{name} evidence must be between 0 and 1"
            )

        normalized[name] = value

    return normalized


def _validate_weights(
    weights: dict[str, float],
) -> dict[str, float]:
    result = {}

    for name in DEFAULT_WEIGHTS:
        value = float(
            weights.get(
                name,
                DEFAULT_WEIGHTS[name],
            )
        )

        if value < 0:
            raise ValueError(
                f"{name} weight must be >= 0"
            )

        result[name] = value

    if sum(result.values()) <= 0:
        raise ValueError(
            "At least one weight must be > 0"
        )

    return result


def classify_reliability(
    score: float,
    thresholds: dict[str, float] | None = None,
) -> str:
    t = dict(
        thresholds
        if thresholds is not None
        else DEFAULT_THRESHOLDS
    )

    normal = float(t["normal"])
    degraded = float(t["degraded"])
    suspect = float(t["suspect"])

    if not (
        0.0 <= suspect < degraded < normal <= 1.0
    ):
        raise ValueError(
            "Thresholds must satisfy "
            "0 <= suspect < degraded < normal <= 1"
        )

    if score >= normal:
        return "NORMAL"

    if score >= degraded:
        return "DEGRADED"

    if score >= suspect:
        return "SUSPECT"

    return "UNTRUSTED"


def evaluate_reliability(
    evidence: dict[str, float],
    weights: dict[str, float] | None = None,
    thresholds: dict[str, float] | None = None,
) -> ReliabilityResult:
    normalized = _validate_evidence(evidence)

    effective_weights = _validate_weights(
        weights or DEFAULT_WEIGHTS
    )

    weighted_sum = sum(
        normalized[name] * effective_weights[name]
        for name in normalized
    )

    total_weight = sum(effective_weights.values())

    score = weighted_sum / total_weight

    state = classify_reliability(
        score,
        thresholds,
    )

    return ReliabilityResult(
        score=score,
        state=state,
        evidence=normalized,
        weights=effective_weights,
    )
'''

test = r'''
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
    evidence = dict(NORMAL)
    evidence["communication"] = 0.0

    result = evaluate_reliability(evidence)

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

    assert result.score == 0.5
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

    assert result.score == 0.1
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

    assert result.score == 0.0
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
'''

(research_dir / "candidate_reliability.py").write_text(
    module,
    encoding="utf-8",
)

Path("stage10_step5_1_verify.py").write_text(
    test,
    encoding="utf-8",
)

print("=" * 70)
print("STAGE 10 - STEP 5.1")
print("CANDIDATE RELIABILITY EVALUATOR CREATED")
print("=" * 70)
print("MODULE=app/research/candidate_reliability.py")
print("EVIDENCE_DIMENSIONS=6")
print("RELIABILITY_SCORE=IMPLEMENTED")
print("STATE_CLASSIFICATION=IMPLEMENTED")
print("CONFIGURABLE_WEIGHTS=YES")
print("CONFIGURABLE_THRESHOLDS=YES")
print("PRODUCTION_STATE_MODIFIED=NO")
print("DATABASE_MODIFIED=NO")
print("MIGRATION_CREATED=NO")
print("=" * 70)
