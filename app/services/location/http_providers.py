from __future__ import annotations

import os
import time
from typing import Any

import requests

from app.services.location.models import (
    GeoPoint,
    GeocodedLocation,
    RouteResult,
    MatrixResult,
)
from app.services.location.providers import (
    GeocodingProvider,
    RoutingProvider,
)


DEFAULT_NOMINATIM_URL = (
    "https://nominatim.openstreetmap.org"
)

DEFAULT_OSRM_URL = (
    "https://router.project-osrm.org"
)

DEFAULT_TIMEOUT_SECONDS = 12.0
DEFAULT_RETRIES = 2

USER_AGENT = (
    "V2V-Backend/1.0 "
    "(vehicle communication prototype)"
)


class LocationProviderError(RuntimeError):
    """Raised when an external location provider fails."""


def _request_json(
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    retries: int = DEFAULT_RETRIES,
) -> dict[str, Any]:

    last_error: Exception | None = None

    for attempt in range(retries + 1):

        try:
            response = requests.request(
                method=method,
                url=url,
                params=params,
                timeout=timeout,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json",
                },
            )

            # Retry transient server failures.
            if response.status_code >= 500:
                last_error = LocationProviderError(
                    f"Provider HTTP {response.status_code}"
                )

                if attempt < retries:
                    time.sleep(
                        0.5 * (attempt + 1)
                    )
                    continue

                raise last_error

            if response.status_code >= 400:
                raise LocationProviderError(
                    f"Provider HTTP {response.status_code}: "
                    f"{response.text[:300]}"
                )

            try:
                data = response.json()
            except ValueError as exc:
                raise LocationProviderError(
                    "Provider returned invalid JSON"
                ) from exc

            if not isinstance(data, (dict, list)):
                raise LocationProviderError(
                    "Provider returned unexpected JSON structure"
                )

            return data

        except requests.Timeout as exc:
            last_error = LocationProviderError(
                "Location provider request timed out"
            )

            if attempt < retries:
                time.sleep(
                    0.5 * (attempt + 1)
                )
                continue

            raise last_error from exc

        except requests.RequestException as exc:
            last_error = LocationProviderError(
                f"Location provider request failed: {exc}"
            )

            if attempt < retries:
                time.sleep(
                    0.5 * (attempt + 1)
                )
                continue

            raise last_error from exc

    raise LocationProviderError(
        f"Location provider failed: {last_error}"
    )


class NominatimGeocodingProvider(
    GeocodingProvider
):

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.base_url = (
            base_url
            or os.getenv(
                "NOMINATIM_BASE_URL",
                DEFAULT_NOMINATIM_URL,
            )
        ).rstrip("/")

        self.timeout = timeout

    def geocode(
        self,
        query: str,
    ) -> GeocodedLocation:

        data = _request_json(
            "GET",
            f"{self.base_url}/search",
            params={
                "q": query,
                "format": "jsonv2",
                "limit": 1,
            },
            timeout=self.timeout,
        )

        results = data

        # Nominatim returns a JSON list, so the generic
        # object helper cannot be used here.
        if not isinstance(results, list):
            raise LocationProviderError(
                "Nominatim returned an unexpected response"
            )

        if not results:
            raise LocationProviderError(
                f"No location found for '{query}'"
            )

        item = results[0]

        try:
            latitude = float(item["lat"])
            longitude = float(item["lon"])
        except (KeyError, TypeError, ValueError) as exc:
            raise LocationProviderError(
                "Nominatim returned invalid coordinates"
            ) from exc

        return GeocodedLocation(
            query=query,
            latitude=latitude,
            longitude=longitude,
            display_name=item.get(
                "display_name",
                query,
            ),
            provider="nominatim",
        )

    def reverse_geocode(
        self,
        point: GeoPoint,
    ) -> GeocodedLocation:

        data = _request_json(
            "GET",
            f"{self.base_url}/reverse",
            params={
                "lat": point.latitude,
                "lon": point.longitude,
                "format": "jsonv2",
            },
            timeout=self.timeout,
        )

        try:
            display_name = data["display_name"]
        except KeyError as exc:
            raise LocationProviderError(
                "Nominatim reverse-geocode response "
                "did not contain display_name"
            ) from exc

        return GeocodedLocation(
            query=f"{point.latitude},{point.longitude}",
            latitude=float(point.latitude),
            longitude=float(point.longitude),
            display_name=display_name,
            provider="nominatim",
        )


class OSRMRoutingProvider(
    RoutingProvider
):

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        retries: int = DEFAULT_RETRIES,
    ):
        self.base_url = (
            base_url
            or os.getenv(
                "OSRM_BASE_URL",
                DEFAULT_OSRM_URL,
            )
        ).rstrip("/")

        self.timeout = timeout
        self.retries = retries

    @staticmethod
    def _coordinates(
        points: list[GeoPoint],
    ) -> str:

        if len(points) < 2:
            raise ValueError(
                "At least two points are required"
            )

        values = []

        for point in points:

            if not (
                -90.0
                <= float(point.latitude)
                <= 90.0
            ):
                raise ValueError(
                    "Latitude outside valid range"
                )

            if not (
                -180.0
                <= float(point.longitude)
                <= 180.0
            ):
                raise ValueError(
                    "Longitude outside valid range"
                )

            # OSRM requires longitude,latitude.
            values.append(
                f"{float(point.longitude)},"
                f"{float(point.latitude)}"
            )

        return ";".join(values)

    def route(
        self,
        points: list[GeoPoint],
    ) -> RouteResult:

        coordinates = self._coordinates(points)

        url = (
            f"{self.base_url}"
            f"/route/v1/driving/"
            f"{coordinates}"
        )

        data = _request_json(
            "GET",
            url,
            params={
                "overview": "full",
                "geometries": "geojson",
                "steps": "false",
            },
            timeout=self.timeout,
            retries=self.retries,
        )

        if data.get("code") != "Ok":
            raise LocationProviderError(
                f"OSRM route failed: "
                f"{data.get('code', 'UNKNOWN')}"
            )

        routes = data.get("routes")

        if not isinstance(routes, list) or not routes:
            raise LocationProviderError(
                "OSRM returned no route"
            )

        route = routes[0]

        geometry = route.get("geometry")

        if not isinstance(geometry, dict):
            raise LocationProviderError(
                "OSRM route geometry missing"
            )

        distance = route.get("distance")
        duration = route.get("duration")

        if distance is None or duration is None:
            raise LocationProviderError(
                "OSRM route distance/duration missing"
            )

        return RouteResult(
            provider="osrm",
            geometry=geometry,
            distance_meters=float(distance),
            duration_seconds=int(round(float(duration))),
            traffic_available=False,
            traffic_status="TRAFFIC_UNAVAILABLE",
        )

    def matrix(
        self,
        points: list[GeoPoint],
    ) -> MatrixResult:

        coordinates = self._coordinates(points)

        url = (
            f"{self.base_url}"
            f"/table/v1/driving/"
            f"{coordinates}"
        )

        data = _request_json(
            "GET",
            url,
            params={
                "annotations": "distance,duration",
            },
            timeout=self.timeout,
            retries=self.retries,
        )

        if data.get("code") != "Ok":
            raise LocationProviderError(
                f"OSRM matrix failed: "
                f"{data.get('code', 'UNKNOWN')}"
            )

        distances = data.get("distances")
        durations = data.get("durations")

        if not isinstance(distances, list):
            raise LocationProviderError(
                "OSRM matrix distances missing"
            )

        if not isinstance(durations, list):
            raise LocationProviderError(
                "OSRM matrix durations missing"
            )

        return MatrixResult(
            provider="osrm",
            distances_meters=distances,
            durations_seconds=durations,
            traffic_available=False,
            traffic_status="TRAFFIC_UNAVAILABLE",
        )
