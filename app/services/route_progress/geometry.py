import json
import math
from dataclasses import dataclass


EARTH_RADIUS_M = 6371008.8


@dataclass(frozen=True)
class PolylinePoint:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class ProjectionResult:
    latitude: float
    longitude: float
    distance_from_route_m: float
    along_route_m: float
    segment_index: int


def haversine_m(
    latitude1: float,
    longitude1: float,
    latitude2: float,
    longitude2: float,
) -> float:
    phi1 = math.radians(latitude1)
    phi2 = math.radians(latitude2)
    d_phi = math.radians(latitude2 - latitude1)
    d_lambda = math.radians(longitude2 - longitude1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1)
        * math.cos(phi2)
        * math.sin(d_lambda / 2) ** 2
    )

    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def _project_local(
    point: PolylinePoint,
    start: PolylinePoint,
    end: PolylinePoint,
) -> tuple[float, float, float]:
    lat0 = math.radians(point.latitude)
    scale_x = EARTH_RADIUS_M * math.cos(lat0)
    scale_y = EARTH_RADIUS_M

    px = math.radians(point.longitude) * scale_x
    py = math.radians(point.latitude) * scale_y

    sx = math.radians(start.longitude) * scale_x
    sy = math.radians(start.latitude) * scale_y

    ex = math.radians(end.longitude) * scale_x
    ey = math.radians(end.latitude) * scale_y

    dx = ex - sx
    dy = ey - sy

    length_sq = dx * dx + dy * dy

    if length_sq <= 1e-12:
        t = 0.0
    else:
        t = ((px - sx) * dx + (py - sy) * dy) / length_sq
        t = max(0.0, min(1.0, t))

    qx = sx + t * dx
    qy = sy + t * dy

    distance = math.hypot(px - qx, py - qy)

    projected_lat = math.degrees(qy / scale_y)
    projected_lon = math.degrees(qx / scale_x)

    return projected_lat, projected_lon, distance


def parse_route_geometry(geometry: str | dict) -> list[PolylinePoint]:
    if isinstance(geometry, str):
        payload = json.loads(geometry)
    elif isinstance(geometry, dict):
        payload = geometry
    else:
        raise ValueError("Unsupported route geometry format")

    if payload.get("type") == "Feature":
        payload = payload.get("geometry") or {}

    if payload.get("type") == "FeatureCollection":
        features = payload.get("features") or []

        if not features:
            raise ValueError("Route geometry contains no features")

        payload = features[0].get("geometry") or {}

    geometry_type = payload.get("type")

    if geometry_type != "LineString":
        raise ValueError(
            f"Route geometry must be GeoJSON LineString, got {geometry_type!r}"
        )

    coordinates = payload.get("coordinates") or []

    if len(coordinates) < 2:
        raise ValueError("Route geometry must contain at least two points")

    points = []

    for coordinate in coordinates:
        if len(coordinate) < 2:
            raise ValueError("Invalid route coordinate")

        longitude = float(coordinate[0])
        latitude = float(coordinate[1])

        if not (-90 <= latitude <= 90):
            raise ValueError("Route latitude is outside valid range")

        if not (-180 <= longitude <= 180):
            raise ValueError("Route longitude is outside valid range")

        points.append(
            PolylinePoint(
                latitude=latitude,
                longitude=longitude,
            )
        )

    return points


def project_point_to_route(
    latitude: float,
    longitude: float,
    route_points: list[PolylinePoint],
) -> ProjectionResult:
    if len(route_points) < 2:
        raise ValueError("At least two route points are required")

    vehicle_point = PolylinePoint(latitude, longitude)

    best = None
    cumulative = 0.0

    for index in range(len(route_points) - 1):
        start = route_points[index]
        end = route_points[index + 1]

        segment_length = haversine_m(
            start.latitude,
            start.longitude,
            end.latitude,
            end.longitude,
        )

        projected_lat, projected_lon, lateral_distance = _project_local(
            vehicle_point,
            start,
            end,
        )

        candidate = ProjectionResult(
            latitude=projected_lat,
            longitude=projected_lon,
            distance_from_route_m=lateral_distance,
            along_route_m=cumulative + segment_length * (
                haversine_m(
                    start.latitude,
                    start.longitude,
                    projected_lat,
                    projected_lon,
                ) / segment_length
                if segment_length > 0
                else 0.0
            ),
            segment_index=index,
        )

        if best is None or candidate.distance_from_route_m < best.distance_from_route_m:
            best = candidate

        cumulative += segment_length

    return best


def route_length_m(route_points: list[PolylinePoint]) -> float:
    return sum(
        haversine_m(
            route_points[index].latitude,
            route_points[index].longitude,
            route_points[index + 1].latitude,
            route_points[index + 1].longitude,
        )
        for index in range(len(route_points) - 1)
    )
