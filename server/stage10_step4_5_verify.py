
from datetime import datetime, timedelta, timezone

from app.research.metrics import (
    RunMetadata,
    build_configuration_fingerprint,
    calculate_exposure_duration,
    calculate_latency,
    create_metric,
)


START = datetime(
    2026,
    1,
    1,
    12,
    0,
    0,
    tzinfo=timezone.utc,
)

END = START + timedelta(seconds=30)

CONFIG = {
    "fault_type": "COMMUNICATION_LOSS",
    "duration_seconds": 10,
    "target": "TEST-001",
}


def test_fingerprint():
    first = build_configuration_fingerprint(CONFIG)

    second = build_configuration_fingerprint(
        {
            "target": "TEST-001",
            "duration_seconds": 10,
            "fault_type": "COMMUNICATION_LOSS",
        }
    )

    assert first == second
    assert len(first) == 64

    print("CONFIGURATION_FINGERPRINT=PASS")


def test_run_metadata():
    fingerprint = build_configuration_fingerprint(CONFIG)

    run = RunMetadata(
        run_id="RUN-001",
        mechanism_version="stage10-candidate-v0",
        software_version="backend-test",
        configuration_fingerprint=fingerprint,
        random_seed=12345,
        fault_configuration=CONFIG,
        start_time=START,
        end_time=END,
        validity_status="VALID",
    )

    data = run.to_dict()

    assert data["run_id"] == "RUN-001"
    assert data["random_seed"] == 12345
    assert data["validity_status"] == "VALID"
    assert data["exposure_duration_seconds"] == 30.0

    print("RUN_METADATA=PASS")
    print("EXPOSURE_DURATION=PASS")


def test_latency():
    value = calculate_latency(START, END)

    assert value == 30.0

    exposure = calculate_exposure_duration(
        START,
        END,
    )

    assert exposure == 30.0

    print("LATENCY_CALCULATION=PASS")


def test_metrics():
    metric = create_metric(
        run_id="RUN-001",
        metric_name="detection_latency",
        value=2.5,
        unit="seconds",
        timestamp=END,
    )

    data = metric.to_dict()

    assert data["metric_name"] == "detection_latency"
    assert data["value"] == 2.5
    assert data["unit"] == "seconds"
    assert data["validity_status"] == "VALID"

    print("METRIC_RECORD=PASS")


test_fingerprint()
test_run_metadata()
test_latency()
test_metrics()

print("REPRODUCIBILITY_TESTS=PASS")
print("ALL_STEP_4_5_TESTS=PASS")
