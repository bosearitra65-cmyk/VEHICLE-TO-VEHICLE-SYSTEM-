from pathlib import Path

research_dir = Path("app/research")
research_dir.mkdir(parents=True, exist_ok=True)

module = r'''
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


def _utc(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def build_configuration_fingerprint(
    configuration: dict[str, Any],
) -> str:
    canonical = json.dumps(
        configuration,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")

    return hashlib.sha256(canonical).hexdigest()


@dataclass(frozen=True)
class RunMetadata:
    run_id: str
    mechanism_version: str
    software_version: str
    configuration_fingerprint: str
    random_seed: int | None
    fault_configuration: dict[str, Any]
    start_time: datetime
    end_time: datetime | None = None
    validity_status: str = "INCOMPLETE"

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("run_id is required")

        if not self.mechanism_version:
            raise ValueError("mechanism_version is required")

        if not self.software_version:
            raise ValueError("software_version is required")

        if not self.configuration_fingerprint:
            raise ValueError(
                "configuration_fingerprint is required"
            )

        if self.validity_status not in {
            "VALID",
            "INVALID",
            "INCOMPLETE",
        }:
            raise ValueError(
                "invalid validity_status"
            )

    @property
    def exposure_duration_seconds(self) -> float | None:
        if self.end_time is None:
            return None

        return (
            _utc(self.end_time)
            - _utc(self.start_time)
        ).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "mechanism_version": self.mechanism_version,
            "software_version": self.software_version,
            "configuration_fingerprint":
                self.configuration_fingerprint,
            "random_seed": self.random_seed,
            "fault_configuration":
                dict(self.fault_configuration),
            "start_time":
                _utc(self.start_time).isoformat(),
            "end_time":
                (
                    _utc(self.end_time).isoformat()
                    if self.end_time is not None
                    else None
                ),
            "exposure_duration_seconds":
                self.exposure_duration_seconds,
            "validity_status":
                self.validity_status,
        }


@dataclass(frozen=True)
class MetricRecord:
    run_id: str
    metric_name: str
    value: float
    unit: str
    timestamp: datetime
    validity_status: str = "VALID"

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("run_id is required")

        if not self.metric_name:
            raise ValueError("metric_name is required")

        if not self.unit:
            raise ValueError("unit is required")

        if self.validity_status not in {
            "VALID",
            "INVALID",
            "INCOMPLETE",
        }:
            raise ValueError(
                "invalid metric validity_status"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "timestamp":
                _utc(self.timestamp).isoformat(),
            "validity_status":
                self.validity_status,
        }


def calculate_latency(
    start_time: datetime,
    end_time: datetime,
) -> float:
    return (
        _utc(end_time)
        - _utc(start_time)
    ).total_seconds()


def calculate_exposure_duration(
    start_time: datetime,
    end_time: datetime,
) -> float:
    return calculate_latency(start_time, end_time)


def create_metric(
    run_id: str,
    metric_name: str,
    value: float,
    unit: str,
    timestamp: datetime,
    validity_status: str = "VALID",
) -> MetricRecord:
    return MetricRecord(
        run_id=run_id,
        metric_name=metric_name,
        value=float(value),
        unit=unit,
        timestamp=_utc(timestamp),
        validity_status=validity_status,
    )
'''

test = r'''
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
'''

(research_dir / "metrics.py").write_text(
    module,
    encoding="utf-8",
)

Path("stage10_step4_5_verify.py").write_text(
    test,
    encoding="utf-8",
)

print("=" * 70)
print("STAGE 10 - STEP 4.5")
print("REPRODUCIBILITY + METRICS CREATED")
print("=" * 70)
print("MODULE=app/research/metrics.py")
print("VERIFICATION=stage10_step4_5_verify.py")
print("FINGERPRINT=IMPLEMENTED")
print("RUN_METADATA=IMPLEMENTED")
print("RANDOM_SEED=IMPLEMENTED")
print("EXPOSURE_DURATION=IMPLEMENTED")
print("VALIDITY_STATUS=IMPLEMENTED")
print("METRIC_RECORD=IMPLEMENTED")
print("DATABASE_MODIFIED=NO")
print("MIGRATION_CREATED=NO")
print("PRODUCTION_STATE_MODIFIED=NO")
print("=" * 70)
