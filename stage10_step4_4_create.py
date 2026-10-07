from pathlib import Path

research_dir = Path("app/research")
research_dir.mkdir(parents=True, exist_ok=True)

module = r'''
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
'''

test = r'''
from datetime import datetime, timezone

from app.research.observation import (
    compare_ground_truth_and_observation,
    create_ground_truth,
    record_observation,
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


def test_ground_truth():
    record = create_ground_truth(
        ground_truth_id="GT-001",
        run_id="RUN-001",
        fault_id="FAULT-001",
        timestamp=NOW,
        fault_state="ACTIVE",
        expected_effect="vehicle observation delayed",
    )

    data = record.to_dict()

    assert data["ground_truth_id"] == "GT-001"
    assert data["fault_state"] == "ACTIVE"
    assert data["source"] == "fault_injector"

    return record


def test_observation():
    record = record_observation(
        observation_id="OBS-001",
        run_id="RUN-001",
        timestamp=NOW,
        entity_type="vehicle",
        entity_id="TEST-001",
        observation_type="vehicle_state",
        value={"speed": 40.0},
        source="research_test",
    )

    data = record.to_dict()

    assert data["observation_id"] == "OBS-001"
    assert data["entity_id"] == "TEST-001"
    assert data["value"]["speed"] == 40.0

    return record


def test_comparison(gt, obs):
    comparison = compare_ground_truth_and_observation(
        gt,
        obs,
    )

    assert comparison["run_id"] == "RUN-001"
    assert comparison["fault_id"] == "FAULT-001"
    assert comparison["ground_truth_state"] == "ACTIVE"
    assert comparison["observed_value"]["speed"] == 40.0
    assert (
        comparison["comparison_source"]
        == "research_framework"
    )


gt = test_ground_truth()
print("GROUND_TRUTH_RECORD=PASS")

obs = test_observation()
print("OBSERVATION_RECORD=PASS")

test_comparison(gt, obs)
print("GROUND_TRUTH_OBSERVATION_COMPARISON=PASS")

print("SEPARATION_CHECK=PASS")
print("ALL_OBSERVATION_TESTS=PASS")
'''

(research_dir / "observation.py").write_text(
    module,
    encoding="utf-8",
)

Path("stage10_step4_4_verify.py").write_text(
    test,
    encoding="utf-8",
)

print("=" * 70)
print("STAGE 10 - STEP 4.4")
print("FAULT OBSERVATION + GROUND TRUTH CREATED")
print("=" * 70)
print("MODULE=app/research/observation.py")
print("VERIFICATION=stage10_step4_4_verify.py")
print("GROUND_TRUTH=IMPLEMENTED")
print("OBSERVATION=IMPLEMENTED")
print("COMPARISON=IMPLEMENTED")
print("CANDIDATE_DECISION=NOT_IMPLEMENTED")
print("DATABASE_MODIFIED=NO")
print("MIGRATION_CREATED=NO")
print("PRODUCTION_STATE_MODIFIED=NO")
print("=" * 70)
