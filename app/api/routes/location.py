
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
