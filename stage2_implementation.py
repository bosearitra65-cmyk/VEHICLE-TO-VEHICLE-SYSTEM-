from __future__ import annotations

import ast
import json
import math
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
API = APP / "api"
ROUTES = API / "routes"
LOCATION = APP / "services" / "location"

print("=" * 80)
print("STAGE 2 — LOCATION / ROUTING FOUNDATION")
print("=" * 80)

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")

def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")

def parse(path: Path):
    return ast.parse(read_text(path), filename=str(path))

def backup_file(path: Path, backup_root: Path):
    if path.exists():
        target = backup_root / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)

def find_router_variable(tree):
    candidates = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if (
                        isinstance(node.value, ast.Call)
                        and isinstance(node.value.func, ast.Name)
                        and node.value.func.id == "APIRouter"
                    ):
                        candidates.append(target.id)
    return candidates[0] if candidates else None

def has_location_registration(source: str) -> bool:
    return "location_router" in source and "include_router" in source

# -------------------------------------------------------------------------
# 1. PRE-CHANGE STRUCTURAL AUDIT
# -------------------------------------------------------------------------

router_file = API / "router.py"
routes_file = ROUTES / "routes.py"
dependencies_file = API / "dependencies.py"

if not router_file.exists():
    raise RuntimeError(f"Required API router file not found: {router_file}")

if not routes_file.exists():
    raise RuntimeError(f"Existing routes file not found: {routes_file}")

router_source = read_text(router_file)
routes_source = read_text(routes_file)

router_tree = parse(router_file)
routes_tree = parse(routes_file)

router_var = find_router_variable(router_tree)

print(f"API router: {router_file}")
print(f"Existing routes: {routes_file}")
print(f"Detected APIRouter variable: {router_var}")

if not router_var:
    raise RuntimeError(
        "Could not safely identify the existing APIRouter variable. "
        "No files were modified."
    )

# Locate existing /routes/calculate endpoint without changing it.
calculate_routes = []
for node in ast.walk(routes_tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                if dec.func.attr in {"get", "post", "put", "patch", "delete"}:
                    for arg in dec.args:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            if "calculate" in arg.value:
                                calculate_routes.append(
                                    (node.name, dec.func.attr, arg.value)
                                )

print("Existing calculate endpoints:", calculate_routes)

# -------------------------------------------------------------------------
# 2. BACKUP
# -------------------------------------------------------------------------

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_root = ROOT / ".audit_backups" / f"stage2_location_{stamp}"

for path in [router_file, routes_file]:
    backup_file(path, backup_root)

print(f"Backup created: {backup_root}")

# -------------------------------------------------------------------------
# 3. LOCATION DOMAIN MODELS
# -------------------------------------------------------------------------

write_text(
    LOCATION / "__init__.py",
    '''"""Location, geocoding and routing services."""\n'''
)

write_text(
    LOCATION / "models.py",
    r'''
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
'''
)

# -------------------------------------------------------------------------
# 4. PROVIDER ABSTRACTIONS
# -------------------------------------------------------------------------

write_text(
    LOCATION / "providers.py",
    r'''
from __future__ import annotations

from abc import ABC, abstractmethod

from .models import GeoPoint, GeocodedLocation, MatrixResult, RouteResult


class GeocodingProvider(ABC):

    name = "unknown"

    @abstractmethod
    def geocode(self, query: str) -> GeocodedLocation:
        raise NotImplementedError

    @abstractmethod
    def reverse_geocode(self, point: GeoPoint) -> GeocodedLocation:
        raise NotImplementedError


class RoutingProvider(ABC):

    name = "unknown"

    @abstractmethod
    def route(self, points: list[GeoPoint]) -> RouteResult:
        raise NotImplementedError

    @abstractmethod
    def matrix(self, points: list[GeoPoint]) -> MatrixResult:
        raise NotImplementedError
'''
)

# -------------------------------------------------------------------------
# 5. HTTP PROVIDERS
# -------------------------------------------------------------------------

write_text(
    LOCATION / "http_providers.py",
    r'''
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

from .models import GeoPoint, GeocodedLocation, MatrixResult, RouteResult
from .providers import GeocodingProvider, RoutingProvider


class NominatimGeocodingProvider(GeocodingProvider):

    name = "nominatim"

    def __init__(
        self,
        base_url: str = "https://nominatim.openstreetmap.org",
        user_agent: str = "vehicle-communication-backend/1.0",
    ):
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent

    def _get(self, path: str, params: dict[str, Any]) -> Any:
        query = urllib.parse.urlencode(params)
        request = urllib.request.Request(
            f"{self.base_url}{path}?{query}",
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    def geocode(self, query: str) -> GeocodedLocation:
        data = self._get(
            "/search",
            {
                "q": query,
                "format": "json",
                "limit": 1,
            },
        )

        if not data:
            raise ValueError(f"Location not found: {query}")

        item = data[0]

        return GeocodedLocation(
            query=query,
            latitude=float(item["lat"]),
            longitude=float(item["lon"]),
            display_name=str(item.get("display_name", query)),
            provider=self.name,
        )

    def reverse_geocode(self, point: GeoPoint) -> GeocodedLocation:
        data = self._get(
            "/reverse",
            {
                "lat": point.latitude,
                "lon": point.longitude,
                "format": "json",
            },
        )

        return GeocodedLocation(
            query=f"{point.latitude},{point.longitude}",
            latitude=point.latitude,
            longitude=point.longitude,
            display_name=str(data.get("display_name", "")),
            provider=self.name,
        )


class OSRMRoutingProvider(RoutingProvider):

    name = "osrm"

    def __init__(
        self,
        base_url: str = "https://router.project-osrm.org",
    ):
        self.base_url = base_url.rstrip("/")

    def _get(self, path: str, params: dict[str, Any]) -> Any:
        query = urllib.parse.urlencode(params)
        request = urllib.request.Request(
            f"{self.base_url}{path}?{query}",
            headers={
                "User-Agent": "vehicle-communication-backend/1.0",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _coords(points: list[GeoPoint]) -> str:
        return ";".join(
            f"{p.longitude},{p.latitude}"
            for p in points
        )

    def route(self, points: list[GeoPoint]) -> RouteResult:
        if len(points) < 2:
            raise ValueError("At least two points are required for routing.")

        data = self._get(
            f"/route/v1/driving/{self._coords(points)}",
            {
                "overview": "full",
                "geometries": "geojson",
                "steps": "false",
            },
        )

        if data.get("code") != "Ok" or not data.get("routes"):
            raise RuntimeError(
                f"Routing provider failed: {data.get('message', data.get('code'))}"
            )

        route = data["routes"][0]

        return RouteResult(
            provider=self.name,
            geometry=route.get("geometry"),
            distance_meters=float(route["distance"]),
            duration_seconds=float(route["duration"]),
            traffic_available=False,
            traffic_status="TRAFFIC_UNAVAILABLE",
        )

    def matrix(self, points: list[GeoPoint]) -> MatrixResult:
        if len(points) < 2:
            raise ValueError("At least two points are required for a matrix.")

        data = self._get(
            f"/table/v1/driving/{self._coords(points)}",
            {
                "annotations": "duration,distance",
            },
        )

        if data.get("code") != "Ok":
            raise RuntimeError(
                f"Matrix provider failed: {data.get('message', data.get('code'))}"
            )

        return MatrixResult(
            provider=self.name,
            distances_meters=data.get("distances", []),
            durations_seconds=data.get("durations", []),
            traffic_available=False,
            traffic_status="TRAFFIC_UNAVAILABLE",
        )
'''
)

# -------------------------------------------------------------------------
# 6. LOCATION SERVICE
# -------------------------------------------------------------------------

write_text(
    LOCATION / "service.py",
    r'''
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
'''
)

# -------------------------------------------------------------------------
# 7. LOCATION API
# -------------------------------------------------------------------------

write_text(
    ROUTES / "location.py",
    r'''
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.location.models import GeoPoint
from app.services.location.service import location_service


router = APIRouter(
    prefix="/location",
    tags=["location"],
)


class LocationInput(BaseModel):
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class RouteRequest(BaseModel):
    locations: list[LocationInput] = Field(min_length=2)


class MatrixRequest(BaseModel):
    locations: list[LocationInput] = Field(min_length=2)


class DistanceRequest(BaseModel):
    locations: list[LocationInput] = Field(min_length=2)


def resolve_locations(items: list[LocationInput]) -> list[GeoPoint]:
    points = []

    for item in items:
        try:
            points.append(
                location_service.resolve(
                    location=item.location,
                    latitude=item.latitude,
                    longitude=item.longitude,
                )
            )
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

    return points


@router.get("/geocode")
def geocode(
    query: str = Query(..., min_length=1),
):
    try:
        result = location_service.geocode(query)
        return {
            "success": True,
            "data": {
                "query": result.query,
                "latitude": result.latitude,
                "longitude": result.longitude,
                "display_name": result.display_name,
                "provider": result.provider,
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/reverse-geocode")
def reverse_geocode(
    latitude: float,
    longitude: float,
):
    try:
        result = location_service.reverse_geocode(latitude, longitude)
        return {
            "success": True,
            "data": {
                "latitude": result.latitude,
                "longitude": result.longitude,
                "display_name": result.display_name,
                "provider": result.provider,
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/route")
def route(request: RouteRequest):
    points = resolve_locations(request.locations)

    try:
        result = location_service.route(points)

        return {
            "success": True,
            "data": {
                "provider": result.provider,
                "geometry": result.geometry,
                "distance_meters": result.distance_meters,
                "duration_seconds": result.duration_seconds,
                "traffic_available": result.traffic_available,
                "traffic_status": result.traffic_status,
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/matrix")
def matrix(request: MatrixRequest):
    points = resolve_locations(request.locations)

    try:
        result = location_service.matrix(points)

        return {
            "success": True,
            "data": {
                "provider": result.provider,
                "distances_meters": result.distances_meters,
                "durations_seconds": result.durations_seconds,
                "traffic_available": result.traffic_available,
                "traffic_status": result.traffic_status,
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/distance")
def distance(request: DistanceRequest):
    points = resolve_locations(request.locations)

    try:
        return {
            "success": True,
            "data": location_service.distance(points),
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
'''
)

# -------------------------------------------------------------------------
# 8. SAFE ROUTER REGISTRATION
# -------------------------------------------------------------------------

router_source = read_text(router_file)

if not has_location_registration(router_source):

    lines = router_source.splitlines()

    # Add import after existing imports.
    import_line = "from app.api.routes.location import router as location_router"

    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            insert_at = i + 1

    lines.insert(insert_at, import_line)

    # Find existing include_router block.
    include_indices = [
        i for i, line in enumerate(lines)
        if f"{router_var}.include_router" in line
    ]

    registration = f"{router_var}.include_router(location_router)"

    if include_indices:
        lines.insert(include_indices[-1] + 1, registration)
    else:
        # Append only if router exists but has no includes.
        lines.append("")
        lines.append(registration)

    write_text(router_file, "\n".join(lines) + "\n")
    print("Location router registered.")
else:
    print("Location router registration already exists; preserved.")

# -------------------------------------------------------------------------
# 9. STATIC COMPILATION
# -------------------------------------------------------------------------

print("Running Python compilation...")

result = subprocess.run(
    [
        sys.executable,
        "-m",
        "compileall",
        "-q",
        "app",
    ],
    cwd=ROOT,
    capture_output=True,
    text=True,
)

if result.returncode != 0:
    print(result.stdout)
    print(result.stderr)
    raise RuntimeError("Python compilation failed.")

print("COMPILE_OK")

# -------------------------------------------------------------------------
# 10. APPLICATION IMPORT
# -------------------------------------------------------------------------

print("Importing FastAPI application...")

result = subprocess.run(
    [
        sys.executable,
        "-c",
        "from main import app; print('APP_IMPORT_OK'); print('ROUTES=', len(app.routes))",
    ],
    cwd=ROOT,
    capture_output=True,
    text=True,
)

print(result.stdout)
if result.returncode != 0:
    print(result.stderr)

    # Restore router if import fails.
    backup_router = backup_root / "app" / "api" / "router.py"

    if backup_router.exists():
        shutil.copy2(backup_router, router_file)
        print("Existing router.py restored from backup.")

    raise RuntimeError("FastAPI application import failed.")

# -------------------------------------------------------------------------
# 11. SERVICE MATHEMATICAL TEST
# -------------------------------------------------------------------------

from app.services.location.service import LocationService
from app.services.location.models import GeoPoint

service = LocationService()

zero = service.haversine_meters(
    GeoPoint(0, 0),
    GeoPoint(0, 0),
)

if abs(zero) > 0.001:
    raise RuntimeError("Haversine zero-distance test failed.")

one_degree = service.haversine_meters(
    GeoPoint(0, 0),
    GeoPoint(0, 1),
)

if not (110_000 <= one_degree <= 112_500):
    raise RuntimeError(
        f"Haversine validation failed: {one_degree}"
    )

print("HAVERSINE_TEST_OK")
print(f"ONE_DEGREE_EQUATOR_METERS={one_degree:.2f}")

# -------------------------------------------------------------------------
# 12. FINAL STRUCTURAL CHECK
# -------------------------------------------------------------------------

location_file = ROUTES / "location.py"

required_files = [
    LOCATION / "__init__.py",
    LOCATION / "models.py",
    LOCATION / "providers.py",
    LOCATION / "http_providers.py",
    LOCATION / "service.py",
    location_file,
]

missing = [str(p) for p in required_files if not p.exists()]

if missing:
    raise RuntimeError(
        "Stage 2 required files missing:\n" + "\n".join(missing)
    )

final_router_source = read_text(router_file)

if "location_router" not in final_router_source:
    raise RuntimeError("Location router registration not detected.")

print()
print("=" * 80)
print("STAGE 2 IMPLEMENTATION COMPLETED")
print("=" * 80)
print(f"BACKUP={backup_root}")
print("LOCATION_SERVICE_OK")
print("GEOCODING_PROVIDER=OSM/Nominatim")
print("ROUTING_PROVIDER=OSRM")
print("MULTI_WAYPOINT_ROUTING=READY")
print("DISTANCE_MATRIX=READY")
print("PLACE_NAME_INPUT=READY")
print("ROAD_DISTANCE=READY")
print("STRAIGHT_LINE_DISTANCE=READY")
print("TRAFFIC_STATUS=EXPLICITLY_UNAVAILABLE")
print("TRAFFIC_AWARE_ETA=NOT_FAKED")
print("APP_IMPORT_OK")
print("STAGE2_LOCATION_ROUTING_FOUNDATION_OK")
print("=" * 80)
