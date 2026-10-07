
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GeoPoint:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class GeocodedLocation:
    query: str
    latitude: float
    longitude: float
    display_name: str
    provider: str


@dataclass(frozen=True)
class RouteResult:
    provider: str
    geometry: Optional[dict]
    distance_meters: float
    duration_seconds: float
    traffic_available: bool = False
    traffic_status: str = "TRAFFIC_UNAVAILABLE"


@dataclass(frozen=True)
class MatrixResult:
    provider: str
    distances_meters: list[list[float | None]]
    durations_seconds: list[list[float | None]]
    traffic_available: bool = False
    traffic_status: str = "TRAFFIC_UNAVAILABLE"
