from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_resource_access
from app.auth.permissions import Permission
from app.models.user import User
from app.schemas.common import APIResponse
from app.services.route_progress.service import (
    DEFAULT_DEVIATION_THRESHOLD_M,
    calculate_route_progress,
    calculate_vehicle_route_progress,
)
from app.utils.identifiers import generate_request_id


router = APIRouter(
    tags=["route-progress"],
)


def _result_dict(result):
    return {
        "vehicle_id": result.vehicle_id,
        "route_id": result.route_id,
        "route_version": result.route_version,
        "progress_percent": result.progress_percent,
        "distance_travelled_m": result.distance_travelled_m,
        "distance_remaining_m": result.distance_remaining_m,
        "distance_from_route_m": result.distance_from_route_m,
        "deviation_threshold_m": result.deviation_threshold_m,
        "deviation_status": result.deviation_status,
        "current_stop_id": result.current_stop_id,
        "current_stop_name": result.current_stop_name,
        "next_stop_id": result.next_stop_id,
        "next_stop_name": result.next_stop_name,
        "completed_stop_ids": result.completed_stop_ids,
        "route_completed": result.route_completed,
    }


@router.get(
    "/vehicles/{vehicle_id}/route-progress",
    response_model=APIResponse[dict],
)
def vehicle_route_progress(
    vehicle_id: str,
    deviation_threshold_m: float = Query(
        default=DEFAULT_DEVIATION_THRESHOLD_M,
        gt=0,
        le=5000,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_resource_access(
            Permission.VEHICLE_VIEW,
            "vehicle",
            "vehicle_id",
        )
    ),
):
    try:
        result = calculate_vehicle_route_progress(
            db=db,
            vehicle_id=vehicle_id,
            deviation_threshold_m=deviation_threshold_m,
        )
    except ValueError as exc:
        message = str(exc)

        if "Vehicle state not found" in message:
            raise HTTPException(
                status_code=404,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=409,
            detail=message,
        ) from exc

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=_result_dict(result),
    )


@router.get(
    "/routes/{route_id}/vehicles/{vehicle_id}/progress",
    response_model=APIResponse[dict],
)
def route_vehicle_progress(
    route_id: str,
    vehicle_id: str,
    deviation_threshold_m: float = Query(
        default=DEFAULT_DEVIATION_THRESHOLD_M,
        gt=0,
        le=5000,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_resource_access(
            Permission.VEHICLE_VIEW,
            "vehicle",
            "vehicle_id",
        )
    ),
):
    try:
        result = calculate_route_progress(
            db=db,
            vehicle_id=vehicle_id,
            route_id=route_id,
            deviation_threshold_m=deviation_threshold_m,
        )
    except ValueError as exc:
        message = str(exc)

        if "Vehicle state not found" in message or "Route not found" in message:
            raise HTTPException(
                status_code=404,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=409,
            detail=message,
        ) from exc

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=_result_dict(result),
    )
