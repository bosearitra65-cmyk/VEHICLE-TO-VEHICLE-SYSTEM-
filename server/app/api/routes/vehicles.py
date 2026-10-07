from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_device_auth, require_resource_access
from app.auth.permissions import Permission
from app.database.repositories.vehicle_repository import VehicleRepository
from app.database.repositories.vehicle_state_repository import VehicleStateRepository
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.vehicles import (
    VehicleAvailabilityOut,
    VehicleFreshnessOut,
    VehicleHistoryOut,
    VehicleStateIn,
    VehicleStateOut,
)
from app.services.vehicle_availability import get_vehicle_availability
from app.services.vehicle_freshness import get_vehicle_freshness
from app.services.vehicle_history_service import get_vehicle_history
from app.services.vehicle_ingestion import ingest_vehicle_state
from app.utils.identifiers import generate_request_id


router = APIRouter(
    prefix="/vehicle",
    tags=["vehicles"],
)


@router.post(
    "/state",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
)
def receive_vehicle_state(
    payload: VehicleStateIn,
    db: Session = Depends(get_db),
    authenticated_device = Depends(require_device_auth),
):
    if authenticated_device is not None:
        if authenticated_device.vehicle_id != payload.vehicle_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Authenticated device is not assigned to this vehicle",
            )
        if payload.device_id != authenticated_device.device_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Payload device_id does not match authenticated device",
            )

    state = ingest_vehicle_state(db, payload)

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data={
            "vehicle_id": state.vehicle_id,
            "sequence_number": state.sequence_number,
            "timestamp": state.timestamp,
            "latitude": state.latitude,
            "longitude": state.longitude,
            "speed": state.speed,
            "heading": state.heading,
            "communication_status": state.communication_status,
        },
    )


@router.get(
    "/{vehicle_id}/state",
    response_model=APIResponse[VehicleStateOut],
    status_code=status.HTTP_200_OK,
)
def get_vehicle_state(
    vehicle_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_resource_access(
            Permission.VEHICLE_VIEW,
            "vehicle",
            "vehicle_id",
        )
    ),
):
    repository = VehicleStateRepository(db)
    state = repository.get_by_vehicle_id(vehicle_id)

    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle state not found",
        )

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=VehicleStateOut.model_validate(
            state,
            from_attributes=True,
        ),
    )


@router.get(
    "/{vehicle_id}/history",
    response_model=APIResponse[list[VehicleHistoryOut]],
    status_code=status.HTTP_200_OK,
)
def get_vehicle_history_records(
    vehicle_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_resource_access(
            Permission.VEHICLE_VIEW,
            "vehicle",
            "vehicle_id",
        )
    ),
):
    vehicle_repository = VehicleRepository(db)
    vehicle = vehicle_repository.get_by_vehicle_id(vehicle_id)

    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        )

    history = get_vehicle_history(
        db=db,
        vehicle_id=vehicle_id,
    )

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=[
            VehicleHistoryOut.model_validate(
                record,
                from_attributes=True,
            )
            for record in history
        ],
    )


@router.get(
    "/{vehicle_id}/freshness",
    response_model=APIResponse[VehicleFreshnessOut],
    status_code=status.HTTP_200_OK,
)
def get_vehicle_freshness_status(
    vehicle_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_resource_access(
            Permission.VEHICLE_VIEW,
            "vehicle",
            "vehicle_id",
        )
    ),
):
    freshness = get_vehicle_freshness(
        db=db,
        vehicle_id=vehicle_id,
    )

    if freshness is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle state not found",
        )

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=VehicleFreshnessOut(**freshness),
    )


@router.get(
    "/{vehicle_id}/availability",
    response_model=APIResponse[VehicleAvailabilityOut],
    status_code=status.HTTP_200_OK,
)
def get_vehicle_availability_status(
    vehicle_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_resource_access(
            Permission.VEHICLE_VIEW,
            "vehicle",
            "vehicle_id",
        )
    ),
):
    availability = get_vehicle_availability(
        db=db,
        vehicle_id=vehicle_id,
    )

    if availability is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle state not found",
        )

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=VehicleAvailabilityOut(**availability),
    )
