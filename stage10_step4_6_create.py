from pathlib import Path

test = r'''
from datetime import datetime, timedelta, timezone
import subprocess
import sys

from app.research.fault_injection import (
    FaultScenario,
    apply_fault,
)
from app.research.observation import (
    compare_ground_truth_and_observation,
    create_ground_truth,
    record_observation,
)
from app.research.metrics import (
    RunMetadata,
    build_configuration_fingerprint,
    create_metric,
)


RUN_ID = "STAGE10-STEP4-ACCEPTANCE-001"

BASE_TIME = datetime(
    2026,
    1,
    1,
    12,
    0,
    0,
    tzinfo=timezone.utc,
)

BASE_OBSERVATION = {
    "vehicle_id": "TEST-001",
    "timestamp": BASE_TIME.isoformat(),
    "latitude": 22.5726,
    "longitude": 88.3639,
    "speed": 40.0,
}


def make_scenario(fault_type, parameters):
    return FaultScenario(
        fault_id=f"ACCEPT-{fault_type}",
        fault_type=fault_type,
        target="TEST-001",
        activation_time=BASE_TIME,
        duration_seconds=60,
        parameters=parameters,
    )


def verify_fault_pipeline(fault_type, parameters):
    scenario = make_scenario(
        fault_type,
        parameters,
    )

    evaluation_time = (
        BASE_TIME + timedelta(seconds=10)
    )

    transformed = apply_fault(
        BASE_OBSERVATION,
        scenario,
        evaluation_time,
    )

    ground_truth = create_ground_truth(
        ground_truth_id=f"GT-{fault_type}",
        run_id=RUN_ID,
        fault_id=scenario.fault_id,
        timestamp=evaluation_time,
        fault_state="ACTIVE",
        expected_effect=fault_type,
    )

    if fault_type == "COMMUNICATION_LOSS":
        assert transformed is None
        observed_value = {
            "delivery": "lost",
        }
    else:
        assert transformed is not None
        observed_value = transformed

    observation = record_observation(
        observation_id=f"OBS-{fault_type}",
        run_id=RUN_ID,
        timestamp=evaluation_time,
        entity_type="vehicle",
        entity_id="TEST-001",
        observation_type=fault_type,
        value=observed_value,
        source="fault_injection_test",
    )

    comparison = compare_ground_truth_and_observation(
        ground_truth,
        observation,
    )

    assert comparison["run_id"] == RUN_ID
    assert comparison["fault_id"] == scenario.fault_id
    assert comparison["ground_truth_state"] == "ACTIVE"
    assert comparison["expected_effect"] == fault_type

    return True


assert verify_fault_pipeline(
    "COMMUNICATION_DELAY",
    {"delay_seconds": 5},
)
print("PIPELINE_DELAY=PASS")

assert verify_fault_pipeline(
    "COMMUNICATION_LOSS",
    {},
)
print("PIPELINE_LOSS=PASS")

assert verify_fault_pipeline(
    "STALE_STATE",
    {"stale_seconds": 30},
)
print("PIPELINE_STALE=PASS")

assert verify_fault_pipeline(
    "GPS_POSITION_OFFSET",
    {
        "north_meters": 100,
        "east_meters": 100,
    },
)
print("PIPELINE_GPS_OFFSET=PASS")


configuration = {
    "run_id": RUN_ID,
    "mechanism_version": "stage10-candidate-v0",
    "faults": [
        "COMMUNICATION_DELAY",
        "COMMUNICATION_LOSS",
        "STALE_STATE",
        "GPS_POSITION_OFFSET",
    ],
}

fingerprint_1 = build_configuration_fingerprint(
    configuration
)

fingerprint_2 = build_configuration_fingerprint(
    {
        "faults": [
            "COMMUNICATION_DELAY",
            "COMMUNICATION_LOSS",
            "STALE_STATE",
            "GPS_POSITION_OFFSET",
        ],
        "mechanism_version": "stage10-candidate-v0",
        "run_id": RUN_ID,
    }
)

assert fingerprint_1 == fingerprint_2
assert len(fingerprint_1) == 64
print("DETERMINISTIC_FINGERPRINT=PASS")


run = RunMetadata(
    run_id=RUN_ID,
    mechanism_version="stage10-candidate-v0",
    software_version="backend-stage10-step4",
    configuration_fingerprint=fingerprint_1,
    random_seed=20261007,
    fault_configuration=configuration,
    start_time=BASE_TIME,
    end_time=BASE_TIME + timedelta(seconds=60),
    validity_status="VALID",
)

run_data = run.to_dict()

assert run_data["run_id"] == RUN_ID
assert run_data["validity_status"] == "VALID"
assert run_data["random_seed"] == 20261007
assert run_data["exposure_duration_seconds"] == 60.0
print("RUN_METADATA_INTEGRATION=PASS")
print("EXPOSURE_DURATION_INTEGRATION=PASS")


metric = create_metric(
    run_id=RUN_ID,
    metric_name="detection_latency",
    value=2.5,
    unit="seconds",
    timestamp=BASE_TIME + timedelta(seconds=62),
)

metric_data = metric.to_dict()

assert metric_data["run_id"] == RUN_ID
assert metric_data["metric_name"] == "detection_latency"
assert metric_data["validity_status"] == "VALID"
print("METRIC_INTEGRATION=PASS")


# Compile every active application Python source file.
files = sorted(Path("app").rglob("*.py"))

for path in files:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(path),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("COMPILE_FAILURE_FILE=" + str(path))
        print(result.stderr)
        raise SystemExit(1)

print(f"ACTIVE_APP_PYTHON_FILES_COMPILED={len(files)}")
print("ACTIVE_SOURCE_COMPILE=PASS")

print("DATABASE_MODIFIED=NO")
print("MIGRATION_CREATED=NO")
print("PRODUCTION_STATE_MODIFIED=NO")

print("STAGE_10_STEP_4_INTEGRATION=PASS")
'''

Path("stage10_step4_6_acceptance.py").write_text(
    test,
    encoding="utf-8",
)

print("=" * 70)
print("STAGE 10 - STEP 4.6")
print("FINAL INTEGRATION + ACCEPTANCE TEST CREATED")
print("=" * 70)
print("VERIFICATION=stage10_step4_6_acceptance.py")
print("DATABASE_MODIFIED=NO")
print("MIGRATION_CREATED=NO")
print("PRODUCTION_STATE_MODIFIED=NO")
print("=" * 70)
