from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_permission
from app.auth.permissions import Permission
from app.models.user import User
from app.schemas.common import APIResponse
from app.services.operational_intelligence.service import (
    calculate_convoy_operational_intelligence,
    calculate_journey_operational_intelligence,
    calculate_vehicle_operational_intelligence,
)
from app.utils.identifiers import generate_request_id


router = APIRouter(
    tags=["Operational Intelligence"],
)


def _response(data):
    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=data,
    )


@router.get(
    "/vehicles/{vehicle_id}/route-intelligence",
    response_model=APIResponse[dict],
)
def vehicle_route_intelligence(
    vehicle_id: str,
    deviation_threshold_m: float = Query(
        default=100.0,
        gt=0,
        le=5000,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission(Permission.VEHICLE_VIEW)
    ),
):
    try:
        result = calculate_vehicle_operational_intelligence(
            db=db,
            vehicle_id=vehicle_id,
            deviation_threshold_m=deviation_threshold_m,
        )
    except ValueError as exc:
        message = str(exc)
        code = 404 if (
            "not found" in message.lower()
        ) else 409
        raise HTTPException(
            status_code=code,
            detail=message,
        ) from exc

    return _response(result.to_dict())


@router.get(
    "/routes/{route_id}/vehicles/{vehicle_id}/intelligence",
    response_model=APIResponse[dict],
)
def route_vehicle_intelligence(
    route_id: str,
    vehicle_id: str,
    deviation_threshold_m: float = Query(
        default=100.0,
        gt=0,
        le=5000,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission(Permission.VEHICLE_VIEW)
    ),
):
    try:
        result = calculate_vehicle_operational_intelligence(
            db=db,
            vehicle_id=vehicle_id,
            route_id=route_id,
            deviation_threshold_m=deviation_threshold_m,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    if result.route_id != route_id:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Vehicle {vehicle_id} is not operating on route "
                f"{route_id}"
            ),
        )

    return _response(result.to_dict())


@router.get(
    "/convoys/{convoy_id}/operational-intelligence",
    response_model=APIResponse[dict],
)
def convoy_operational_intelligence(
    convoy_id: str,
    deviation_threshold_m: float = Query(
        default=100.0,
        gt=0,
        le=5000,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission(Permission.VEHICLE_VIEW)
    ),
):
    try:
        result = calculate_convoy_operational_intelligence(
            db=db,
            convoy_id=convoy_id,
            deviation_threshold_m=deviation_threshold_m,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return _response(result.to_dict())


@router.get(
    "/journeys/{journey_id}/operational-intelligence",
    response_model=APIResponse[dict],
)
def journey_operational_intelligence(
    journey_id: str,
    deviation_threshold_m: float = Query(
        default=100.0,
        gt=0,
        le=5000,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission(Permission.JOURNEY_VIEW)
    ),
):
    try:
        result = calculate_journey_operational_intelligence(
            db=db,
            journey_id=journey_id,
            deviation_threshold_m=deviation_threshold_m,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return _response(result)
