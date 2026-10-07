from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_permission, require_resource_access
from app.auth.permissions import Permission
from app.database.repositories.vehicle_repository import VehicleRepository
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.operational import VehicleCreate, VehicleOut, VehicleUpdate
from app.utils.identifiers import generate_request_id


router = APIRouter(prefix="/vehicles", tags=["vehicle-management"])


@router.get("", response_model=APIResponse[list[VehicleOut]])
def list_vehicles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VEHICLE_VIEW)),
):
    vehicles = VehicleRepository(db).list_all()

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=[VehicleOut.model_validate(v) for v in vehicles],
    )


@router.post(
    "",
    response_model=APIResponse[VehicleOut],
    status_code=status.HTTP_201_CREATED,
)
def create_vehicle(
    payload: VehicleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VEHICLE_MANAGE)),
):
    repository = VehicleRepository(db)

    if repository.get_by_vehicle_id(payload.vehicle_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vehicle already exists",
        )

    try:
        vehicle = repository.create(
            vehicle_id=payload.vehicle_id,
            device_id=payload.device_id,
            name=payload.name,
        )
        db.commit()
        db.refresh(vehicle)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vehicle identifier or device identifier already exists",
        ) from exc

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=VehicleOut.model_validate(vehicle),
    )


@router.get(
    "/{vehicle_id}",
    response_model=APIResponse[VehicleOut],
)
def get_vehicle(
    vehicle_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_resource_access(Permission.VEHICLE_VIEW, "vehicle", "vehicle_id")
    ),
):
    vehicle = VehicleRepository(db).get_by_vehicle_id(vehicle_id)

    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=VehicleOut.model_validate(vehicle),
    )


@router.patch(
    "/{vehicle_id}",
    response_model=APIResponse[VehicleOut],
)
def update_vehicle(
    vehicle_id: str,
    payload: VehicleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VEHICLE_MANAGE)),
):
    repository = VehicleRepository(db)
    vehicle = repository.get_by_vehicle_id(vehicle_id)

    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    try:
        vehicle = repository.update(
            vehicle,
            device_id=payload.device_id,
            name=payload.name,
            is_active=payload.is_active,
        )
        db.commit()
        db.refresh(vehicle)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Device identifier already belongs to another vehicle",
        ) from exc

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=VehicleOut.model_validate(vehicle),
    )
