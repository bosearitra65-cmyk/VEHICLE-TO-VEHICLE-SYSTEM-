
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
