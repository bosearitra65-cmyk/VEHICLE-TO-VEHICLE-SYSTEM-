from __future__ import annotations

from dataclasses import dataclass
from typing import Any


_SEVERITY_RANK = {
    "NONE": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
}


@dataclass(frozen=True)
class DecisionIntegrationResult:
    vehicle_id: str
    sequence_number: int
    reliability_score: float
    reliability_state: str
    contradiction_severity: str
    contradiction_count: int
    decision_basis: str
    operational_action: str
    read_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "vehicle_id": self.vehicle_id,
            "sequence_number": self.sequence_number,
            "reliability_score": self.reliability_score,
            "reliability_state": self.reliability_state,
            "contradiction_severity": self.contradiction_severity,
            "contradiction_count": self.contradiction_count,
            "decision_basis": self.decision_basis,
            "operational_action": self.operational_action,
            "read_only": self.read_only,
        }


def _severity_name(record: Any) -> str:
    value = getattr(record, "severity", "NONE")
    if hasattr(value, "value"):
        value = value.value
    return str(value).upper()


def integrate_decision(
    *,
    vehicle_id: str,
    sequence_number: int,
    reliability: Any,
    contradictions: tuple[Any, ...] | list[Any] = (),
) -> DecisionIntegrationResult:
    reliability_score = float(getattr(reliability, "score", 0.0))
    reliability_state = str(
        getattr(reliability, "state", "UNTRUSTED")
    ).upper()

    contradiction_list = tuple(contradictions or ())
    severities = [_severity_name(item) for item in contradiction_list]

    highest = max(
        severities,
        key=lambda item: _SEVERITY_RANK.get(item, 0),
        default="NONE",
    )

    basis = (
        "RELIABILITY_ONLY"
        if highest == "NONE"
        else "RELIABILITY_PLUS_CONTRADICTION"
    )

    return DecisionIntegrationResult(
        vehicle_id=vehicle_id,
        sequence_number=int(sequence_number),
        reliability_score=reliability_score,
        reliability_state=reliability_state,
        contradiction_severity=highest,
        contradiction_count=len(contradiction_list),
        decision_basis=basis,
        operational_action="NO_OPERATIONAL_ACTION",
        read_only=True,
    )