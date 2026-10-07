
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


def _utc(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


@dataclass(frozen=True)
class GroundTruthRecord:
    ground_truth_id: str
    run_id: str
    fault_id: str
    timestamp: datetime
    fault_state: str
    expected_effect: str
    source: str = "fault_injector"

    def to_dict(self) -> dict[str, Any]:
        return {
            "ground_truth_id": self.ground_truth_id,
            "run_id": self.run_id,
            "fault_id": self.fault_id,
            "timestamp": _utc(self.timestamp).isoformat(),
            "fault_state": self.fault_state,
            "expected_effect": self.expected_effect,
            "source": self.source,
        }


@dataclass(frozen=True)
class ObservationRecord:
    observation_id: str
    run_id: str
    timestamp: datetime
    entity_type: str
    entity_id: str
    observation_type: str
    value: Any
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "run_id": self.run_id,
            "timestamp": _utc(self.timestamp).isoformat(),
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "observation_type": self.observation_type,
            "value": self.value,
            "source": self.source,
        }


def create_ground_truth(
    ground_truth_id: str,
    run_id: str,
    fault_id: str,
    timestamp: datetime,
    fault_state: str,
    expected_effect: str,
) -> GroundTruthRecord:
    if not ground_truth_id:
        raise ValueError("ground_truth_id is required")
    if not run_id:
        raise ValueError("run_id is required")
    if not fault_id:
        raise ValueError("fault_id is required")
    if not fault_state:
        raise ValueError("fault_state is required")
    if not expected_effect:
        raise ValueError("expected_effect is required")

    return GroundTruthRecord(
        ground_truth_id=ground_truth_id,
        run_id=run_id,
        fault_id=fault_id,
        timestamp=_utc(timestamp),
        fault_state=fault_state,
        expected_effect=expected_effect,
    )


def record_observation(
    observation_id: str,
    run_id: str,
    timestamp: datetime,
    entity_type: str,
    entity_id: str,
    observation_type: str,
    value: Any,
    source: str,
) -> ObservationRecord:
    required = {
        "observation_id": observation_id,
        "run_id": run_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "observation_type": observation_type,
        "source": source,
    }

    missing = [
        name for name, item in required.items()
        if not item
    ]

    if missing:
        raise ValueError(
            "Missing required fields: " + ", ".join(missing)
        )

    return ObservationRecord(
        observation_id=observation_id,
        run_id=run_id,
        timestamp=_utc(timestamp),
        entity_type=entity_type,
        entity_id=entity_id,
        observation_type=observation_type,
        value=value,
        source=source,
    )


def compare_ground_truth_and_observation(
    ground_truth: GroundTruthRecord,
    observation: ObservationRecord,
) -> dict[str, Any]:
    """
    Produces an evidence comparison only.

    It does not make a Candidate decision and does not alter
    authoritative vehicle state.
    """
    return {
        "run_id": ground_truth.run_id,
        "fault_id": ground_truth.fault_id,
        "ground_truth_state": ground_truth.fault_state,
        "expected_effect": ground_truth.expected_effect,
        "observation_type": observation.observation_type,
        "observed_value": observation.value,
        "ground_truth_timestamp": _utc(
            ground_truth.timestamp
        ).isoformat(),
        "observation_timestamp": _utc(
            observation.timestamp
        ).isoformat(),
        "comparison_source": "research_framework",
    }
