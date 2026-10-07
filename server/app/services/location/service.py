
from __future__ import annotations

import math
from typing import Any

from .http_providers import NominatimGeocodingProvider, OSRMRoutingProvider
from .models import GeoPoint, GeocodedLocation, MatrixResult, RouteResult


class LocationService:

    def __init__(self):
        self.geocoder = NominatimGeocodingProvider()
        self.router = OSRMRoutingProvider()

    @staticmethod
    def point(latitude: float, longitude: float) -> GeoPoint:
        if not (-90 <= latitude <= 90):
            raise ValueError("Latitude must be between -90 and 90.")

        if not (-180 <= longitude <= 180):
            raise ValueError("Longitude must be between -180 and 180.")

        return GeoPoint(latitude=latitude, longitude=longitude)

    def geocode(self, query: str) -> GeocodedLocation:
        query = query.strip()

        if not query:
            raise ValueError("Location query cannot be empty.")

        return self.geocoder.geocode(query)

    def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
    ) -> GeocodedLocation:
        return self.geocoder.reverse_geocode(
            self.point(latitude, longitude)
        )

    def resolve(
        self,
        location: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> GeoPoint:
        if location:
            result = self.geocode(location)
            return GeoPoint(result.latitude, result.longitude)

        if latitude is None or longitude is None:
            raise ValueError(
                "Provide either a place name or both latitude and longitude."
            )

        return self.point(latitude, longitude)

    def route(self, points: list[GeoPoint]) -> RouteResult:
        return self.router.route(points)

    def matrix(self, points: list[GeoPoint]) -> MatrixResult:
        return self.router.matrix(points)

    @staticmethod
    def haversine_meters(a: GeoPoint, b: GeoPoint) -> float:
        earth_radius = 6_371_000.0

        lat1 = math.radians(a.latitude)
        lat2 = math.radians(b.latitude)
        dlat = math.radians(b.latitude - a.latitude)
        dlon = math.radians(b.longitude - a.longitude)

        h = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1)
            * math.cos(lat2)
            * math.sin(dlon / 2) ** 2
        )

        return 2 * earth_radius * math.asin(math.sqrt(h))

    def distance(self, points: list[GeoPoint]) -> dict[str, Any]:
        if len(points) < 2:
            raise ValueError("At least two points are required.")

        straight_line = 0.0

        for first, second in zip(points, points[1:]):
            straight_line += self.haversine_meters(first, second)

        result: dict[str, Any] = {
            "point_count": len(points),
            "straight_line_distance_meters": straight_line,
        }

        if len(points) >= 2:
            route = self.route(points)
            result.update(
                {
                    "road_distance_meters": route.distance_meters,
                    "baseline_duration_seconds": route.duration_seconds,
                    "routing_provider": route.provider,
                    "traffic_available": route.traffic_available,
                    "traffic_status": route.traffic_status,
                }
            )

        return result


location_service = LocationService()
