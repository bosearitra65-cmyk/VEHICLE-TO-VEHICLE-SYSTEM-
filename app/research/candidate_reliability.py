
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
