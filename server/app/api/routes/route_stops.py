from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_db,
    require_permission,
    require_resource_access,
)
from app.auth.permissions import Permission
from app.database.repositories.route_repository import RouteRepository
from app.database.repositories.route_stop_repository import RouteStopRepository
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.operational import RouteStopCreate, RouteStopOut
from app.utils.identifiers import generate_request_id


router = APIRouter(
    prefix="/routes/{route_id}/stops",
    tags=["route-stops"],
)


@router.get(
    "",
    response_model=APIResponse[list[RouteStopOut]],
)
def list_route_stops(
    route_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_resource_access(
            Permission.ROUTE_VIEW,
            "route",
            "route_id",
        )
    ),
):
    route_repository = RouteRepository(db)

    route = route_repository.get_by_route_id(route_id)

    if route is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found",
        )

    stops = RouteStopRepository(db).list_by_route(route_id)

    return APIResponse(
        success=True,
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=[
            RouteStopOut.model_validate(stop)
            for stop in stops
        ],
    )


@router.post(
    "",
    response_model=APIResponse[RouteStopOut],
    status_code=status.HTTP_201_CREATED,
)
def create_route_stop(
    route_id: str,
    payload: RouteStopCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_resource_access(
            Permission.ROUTE_MANAGE,
            "route",
            "route_id",
        )
    ),
):
    route_repository = RouteRepository(db)
    stop_repository = RouteStopRepository(db)

    route = route_repository.get_by_route_id(route_id)

    if route is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found",
        )

    if stop_repository.get_by_stop_id(payload.stop_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stop ID already exists",
        )

    if stop_repository.get_by_route_and_sequence(
        route_id,
        payload.sequence,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sequence number already exists for this route",
        )

    if (
        payload.planned_arrival is not None
        and payload.planned_departure is not None
        and payload.planned_departure < payload.planned_arrival
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Planned departure cannot be earlier than planned arrival",
        )

    try:
        stop = stop_repository.create(
            stop_id=payload.stop_id,
            route_id=route_id,
            sequence=payload.sequence,
            name=payload.name,
            latitude=payload.latitude,
            longitude=payload.longitude,
            planned_arrival=payload.planned_arrival,
            planned_departure=payload.planned_departure,
            status=payload.status,
        )

        db.commit()
        db.refresh(stop)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Route stop conflicts with an existing stop",
        )

    return APIResponse(
        success=True,
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=RouteStopOut.model_validate(stop),
    )


@router.get(
    "/{stop_id}",
    response_model=APIResponse[RouteStopOut],
)
def get_route_stop(
    route_id: str,
    stop_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_resource_access(
            Permission.ROUTE_VIEW,
            "route",
            "route_id",
        )
    ),
):
    route = RouteRepository(db).get_by_route_id(route_id)

    if route is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found",
        )

    stop = RouteStopRepository(db).get_by_stop_id(stop_id)

    if stop is None or stop.route_id != route_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route stop not found",
        )

    return APIResponse(
        success=True,
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=RouteStopOut.model_validate(stop),
    )


@router.delete(
    "/{stop_id}",
    response_model=APIResponse[RouteStopOut],
)
def delete_route_stop(
    route_id: str,
    stop_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_resource_access(
            Permission.ROUTE_MANAGE,
            "route",
            "route_id",
        )
    ),
):
    route = RouteRepository(db).get_by_route_id(route_id)

    if route is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found",
        )

    stop_repository = RouteStopRepository(db)
    stop = stop_repository.get_by_stop_id(stop_id)

    if stop is None or stop.route_id != route_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route stop not found",
        )

    response_data = RouteStopOut.model_validate(stop)

    db.delete(stop)
    db.commit()

    return APIResponse(
        success=True,
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=response_data,
    )


