
from datetime import datetime, timedelta, timezone

from app.research.fault_injection import (
    FaultScenario,
    apply_fault,
)


BASE_TIME = datetime(
    2026,
    1,
    1,
    12,
    0,
    0,
    tzinfo=timezone.utc,
)


def base_observation():
    return {
        "vehicle_id": "TEST-001",
        "timestamp": BASE_TIME.isoformat(),
        "latitude": 22.5726,
        "longitude": 88.3639,
        "speed": 40.0,
    }


def scenario(fault_type, **parameters):
    return FaultScenario(
        fault_id=f"TEST-{fault_type}",
        fault_type=fault_type,
        target="TEST-001",
        activation_time=BASE_TIME,
        duration_seconds=60,
        parameters=parameters,
    )


def test_no_fault():
    result = apply_fault(
        base_observation(),
        scenario(
            "COMMUNICATION_DELAY",
            delay_seconds=2,
        ),
        BASE_TIME - timedelta(seconds=1),
    )

    assert result is not None
    assert result["latitude"] == 22.5726
    assert result["fault_injection"]["active"] is False


def test_delay():
    result = apply_fault(
        base_observation(),
        scenario(
            "COMMUNICATION_DELAY",
            delay_seconds=5,
        ),
        BASE_TIME + timedelta(seconds=1),
    )

    assert result is not None
    assert result["fault_injection"]["fault_type"] == (
        "COMMUNICATION_DELAY"
    )
    assert result["fault_injection"]["delivery_time"].endswith(
        "12:00:06+00:00"
    )


def test_loss():
    result = apply_fault(
        base_observation(),
        scenario("COMMUNICATION_LOSS"),
        BASE_TIME + timedelta(seconds=1),
    )

    assert result is None


def test_stale_state():
    result = apply_fault(
        base_observation(),
        scenario(
            "STALE_STATE",
            stale_seconds=30,
        ),
        BASE_TIME + timedelta(seconds=1),
    )

    assert result is not None
    assert result["timestamp"] == (
        BASE_TIME - timedelta(seconds=30)
    ).isoformat()
    assert result["fault_injection"]["stale_seconds"] == 30.0


def test_gps_offset():
    original = base_observation()

    result = apply_fault(
        original,
        scenario(
            "GPS_POSITION_OFFSET",
            north_meters=100,
            east_meters=100,
        ),
        BASE_TIME + timedelta(seconds=1),
    )

    assert result is not None
    assert result["latitude"] != original["latitude"]
    assert result["longitude"] != original["longitude"]
    assert result["fault_injection"]["north_meters"] == 100.0
    assert result["fault_injection"]["east_meters"] == 100.0


print("TEST_NO_FAULT=PASS")
test_no_fault()

print("TEST_DELAY=PASS")
test_delay()

print("TEST_LOSS=PASS")
test_loss()

print("TEST_STALE_STATE=PASS")
test_stale_state()

print("TEST_GPS_OFFSET=PASS")
test_gps_offset()

print("ALL_FAULT_INJECTION_TESTS=PASS")
