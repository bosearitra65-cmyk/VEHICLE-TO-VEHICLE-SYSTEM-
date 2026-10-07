from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AdaptiveResponseResult:
    vehicle_id: str
    sequence_number: int
    reliability_state: str
    contradiction_severity: str
    response: str
    rationale: str
    research_only: bool = True
    operational_action: str = "NO_OPERATIONAL_ACTION"

    def to_dict(self) -> dict[str, Any]:
        return {
            "vehicle_id": self.vehicle_id,
            "sequence_number": self.sequence_number,
            "reliability_state": self.reliability_state,
            "contradiction_severity": self.contradiction_severity,
            "response": self.response,
            "rationale": self.rationale,
            "research_only": self.research_only,
            "operational_action": self.operational_action,
        }


def generate_adaptive_response(
    *,
    vehicle_id: str,
    sequence_number: int,
    reliability_state: str,
    contradiction_severity: str,
) -> AdaptiveResponseResult:
    reliability = str(reliability_state).upper()
    contradiction = str(contradiction_severity).upper()

    if reliability == "UNTRUSTED" or contradiction == "HIGH":
        response = "HOLD_FOR_RECOVERY"
        rationale = "Untrusted reliability or high contradiction requires recovery-oriented research handling."
    elif reliability == "SUSPECT" or contradiction == "MEDIUM":
        response = "REQUIRE_REVALIDATION"
        rationale = "Suspect reliability or medium contradiction requires additional validation."
    elif reliability == "DEGRADED" or contradiction == "LOW":
        response = "INCREASED_OBSERVATION"
        rationale = "Degraded reliability or low contradiction requires increased observation."
    else:
        response = "NORMAL_MONITORING"
        rationale = "Normal reliability with no material contradiction requires normal research monitoring."

    return AdaptiveResponseResult(
        vehicle_id=vehicle_id,
        sequence_number=int(sequence_number),
        reliability_state=reliability,
        contradiction_severity=contradiction,
        response=response,
        rationale=rationale,
        research_only=True,
        operational_action="NO_OPERATIONAL_ACTION",
    )