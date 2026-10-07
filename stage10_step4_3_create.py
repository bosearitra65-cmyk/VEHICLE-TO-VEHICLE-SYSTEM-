from pathlib import Path

research_dir = Path("app/research")
research_dir.mkdir(parents=True, exist_ok=True)

module = r'''
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from math import cos, radians
from typing import Any


SUPPORTED_FAULT_TYPES = {
    "COMMUNICATION_DELAY",
    "COMMUNICATION_LOSS",
    "STALE_STATE",
    "GPS_POSITION_OFFSET",
}


@dataclass(frozen=True)
class FaultScenario:
    fault_id: str
    fault_type: str
    target: str
    activation_time: datetime
    duration_seconds: float
    parameters: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.fault_type not in SUPPORTED_FAULT_TYPES:
            raise ValueError(
                f"Unsupported fault type: {self.fault_type}"
            )

        if self.duration_seconds < 0:
            raise ValueError("duration_seconds must be >= 0")

    @property
    def end_time(self) -> datetime:
        return self.activation_time + timedelta(
            seconds=self.duration_seconds
        )

    def is_active(self, timestamp: datetime) -> bool:
        return self.activation_time <= timestamp < self.end_time


def _ensure_utc(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _offset_gps(
    latitude: float,
    longitude: float,
    north_meters: float,
    east_meters: float,
) -> tuple[float, float]:
    """
    Approximate local displacement.

    This is intentionally deterministic and is used only for
    controlled research fault injection.
    """
    meters_per_degree_lat = 111_320.0
    meters_per_degree_lon = (
        111_320.0 * cos(radians(latitude))
    )

    if abs(meters_per_degree_lon) < 1e-9:
        raise ValueError("Invalid longitude conversion near the pole")

    new_latitude = latitude + (
        north_meters / meters_per_degree_lat
    )

    new_longitude = longitude + (
        east_meters / meters_per_degree_lon
    )

    return new_latitude, new_longitude


def apply_fault(
    observation: dict[str, Any],
    scenario: FaultScenario,
    evaluation_time: datetime,
) -> dict[str, Any] | None:
    """
    Apply one controlled research fault.

    Returns:
        transformed observation, or None when the observation is lost.

    The original observation dictionary is never mutated.
    """
    evaluation_time = _ensure_utc(evaluation_time)

    if not scenario.is_active(evaluation_time):
        result = dict(observation)
        result["fault_injection"] = {
            "fault_id": scenario.fault_id,
            "fault_type": None,
            "active": False,
        }
        return result

    result = dict(observation)

    fault_meta = {
        "fault_id": scenario.fault_id,
        "fault_type": scenario.fault_type,
        "active": True,
        "target": scenario.target,
        "activation_time": _ensure_utc(
            scenario.activation_time
        ).isoformat(),
        "end_time": scenario.end_time.isoformat(),
        "parameters": dict(scenario.parameters),
    }

    if scenario.fault_type == "COMMUNICATION_LOSS":
        return None

    if scenario.fault_type == "COMMUNICATION_DELAY":
        delay_seconds = float(
            scenario.parameters.get("delay_seconds", 0)
        )

        if delay_seconds < 0:
            raise ValueError("delay_seconds must be >= 0")

        fault_meta["delivery_time"] = (
            evaluation_time + timedelta(seconds=delay_seconds)
        ).isoformat()

        result["fault_injection"] = fault_meta
        return result

    if scenario.fault_type == "STALE_STATE":
        stale_seconds = float(
            scenario.parameters.get("stale_seconds", 0)
        )

        if stale_seconds < 0:
            raise ValueError("stale_seconds must be >= 0")

        timestamp_key = scenario.parameters.get(
            "timestamp_field",
            "timestamp",
        )

        if timestamp_key in result:
            original_timestamp = _ensure_utc(
                datetime.fromisoformat(
                    str(result[timestamp_key]).replace("Z", "+00:00")
                )
            )

            result[timestamp_key] = (
                original_timestamp
                - timedelta(seconds=stale_seconds)
            ).isoformat()

        fault_meta["stale_seconds"] = stale_seconds
        result["fault_injection"] = fault_meta
        return result

    if scenario.fault_type == "GPS_POSITION_OFFSET":
        latitude_key = scenario.parameters.get(
            "latitude_field",
            "latitude",
        )
        longitude_key = scenario.parameters.get(
            "longitude_field",
            "longitude",
        )

        if (
            latitude_key not in result
            or longitude_key not in result
        ):
            raise ValueError(
                "GPS_POSITION_OFFSET requires latitude and longitude"
            )

        north_meters = float(
            scenario.parameters.get("north_meters", 0)
        )
        east_meters = float(
            scenario.parameters.get("east_meters", 0)
        )

        latitude, longitude = _offset_gps(
            float(result[latitude_key]),
            float(result[longitude_key]),
            north_meters,
            east_meters,
        )

        result[latitude_key] = latitude
        result[longitude_key] = longitude

        fault_meta["north_meters"] = north_meters
        fault_meta["east_meters"] = east_meters
        result["fault_injection"] = fault_meta
        return result

    raise ValueError(
        f"Unsupported fault type: {scenario.fault_type}"
    )
'''

test = r'''
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
'''

(research_dir / "fault_injection.py").write_text(
    module,
    encoding="utf-8",
)

Path("stage10_step4_3_verify.py").write_text(
    test,
    encoding="utf-8",
)

print("=" * 70)
print("STAGE 10 - STEP 4.3")
print("CONTROLLED FAULT INJECTOR CREATED")
print("=" * 70)
print("MODULE=app/research/fault_injection.py")
print("VERIFICATION=stage10_step4_3_verify.py")
print("SUPPORTED_FAULTS=4")
print("DATABASE_MODIFIED=NO")
print("MIGRATION_CREATED=NO")
print("PRODUCTION_STATE_MODIFIED=NO")
print("=" * 70)
