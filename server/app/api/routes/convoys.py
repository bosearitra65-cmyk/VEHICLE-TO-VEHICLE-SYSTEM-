from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_permission
from app.auth.permissions import Permission
from app.database.repositories.convoy_member_repository import ConvoyMemberRepository
from app.database.repositories.convoy_repository import ConvoyRepository
from app.database.repositories.vehicle_repository import VehicleRepository
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.operational import (
    ConvoyCreate,
    ConvoyMemberCreate,
    ConvoyMemberOut,
    ConvoyOut,
    ConvoyUpdate,
    LeaderUpdate,
)
from app.utils.identifiers import generate_request_id


router = APIRouter(prefix="/convoys", tags=["convoys"])


@router.get("", response_model=APIResponse[list[ConvoyOut]])
def list_convoys(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CONVOY_VIEW)),
):
    convoys = ConvoyRepository(db).list_all()

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=[ConvoyOut.model_validate(item) for item in convoys],
    )


@router.post(
    "",
    response_model=APIResponse[ConvoyOut],
    status_code=status.HTTP_201_CREATED,
)
def create_convoy(
    payload: ConvoyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CONVOY_MANAGE)),
):
    repository = ConvoyRepository(db)

    if payload.leader_vehicle_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Leader must be assigned after convoy membership is created",
        )

    if repository.get_by_convoy_id(payload.convoy_id):
        raise HTTPException(status_code=409, detail="Convoy already exists")

    try:
        convoy = repository.create(
            convoy_id=payload.convoy_id,
            name=payload.name,
            status=payload.status,
        )
        db.commit()
        db.refresh(convoy)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Convoy identifier already exists") from exc

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=ConvoyOut.model_validate(convoy),
    )


@router.get(
    "/{convoy_id}",
    response_model=APIResponse[ConvoyOut],
)
def get_convoy(
    convoy_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CONVOY_VIEW)),
):
    convoy = ConvoyRepository(db).get_by_convoy_id(convoy_id)

    if convoy is None:
        raise HTTPException(status_code=404, detail="Convoy not found")

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=ConvoyOut.model_validate(convoy),
    )


@router.patch(
    "/{convoy_id}",
    response_model=APIResponse[ConvoyOut],
)
def update_convoy(
    convoy_id: str,
    payload: ConvoyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CONVOY_MANAGE)),
):
    repository = ConvoyRepository(db)
    convoy = repository.get_by_convoy_id(convoy_id)

    if convoy is None:
        raise HTTPException(status_code=404, detail="Convoy not found")

    if payload.name is not None:
        convoy.name = payload.name

    if payload.status is not None:
        convoy.status = payload.status

    try:
        db.flush()
        db.commit()
        db.refresh(convoy)
    except Exception:
        db.rollback()
        raise

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=ConvoyOut.model_validate(convoy),
    )


@router.get(
    "/{convoy_id}/members",
    response_model=APIResponse[list[ConvoyMemberOut]],
)
def list_members(
    convoy_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CONVOY_VIEW)),
):
    convoy = ConvoyRepository(db).get_by_convoy_id(convoy_id)

    if convoy is None:
        raise HTTPException(status_code=404, detail="Convoy not found")

    members = ConvoyMemberRepository(db).list_members(
        convoy_id,
        active_only=True,
    )

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=[ConvoyMemberOut.model_validate(item) for item in members],
    )


@router.post(
    "/{convoy_id}/members",
    response_model=APIResponse[ConvoyMemberOut],
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    convoy_id: str,
    payload: ConvoyMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CONVOY_MANAGE)),
):
    convoy_repository = ConvoyRepository(db)
    vehicle_repository = VehicleRepository(db)
    member_repository = ConvoyMemberRepository(db)

    if convoy_repository.get_by_convoy_id(convoy_id) is None:
        raise HTTPException(status_code=404, detail="Convoy not found")

    vehicle = vehicle_repository.get_by_vehicle_id(payload.vehicle_id)

    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    existing = member_repository.get_member(
        convoy_id,
        payload.vehicle_id,
    )

    if existing is not None and existing.status == "active":
        raise HTTPException(status_code=409, detail="Vehicle is already an active convoy member")

    if payload.role == "LEADER":
        raise HTTPException(
            status_code=400,
            detail="Use the administrator leader-assignment endpoint to select the convoy leader",
        )

    try:
        member = member_repository.add_member(
            convoy_id=convoy_id,
            vehicle_id=payload.vehicle_id,
            role=payload.role,
        )
        db.commit()
        db.refresh(member)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Convoy membership conflict") from exc

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=ConvoyMemberOut.model_validate(member),
    )


@router.delete(
    "/{convoy_id}/members/{vehicle_id}",
    response_model=APIResponse[ConvoyMemberOut],
)
def remove_member(
    convoy_id: str,
    vehicle_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CONVOY_MANAGE)),
):
    convoy_repository = ConvoyRepository(db)
    member_repository = ConvoyMemberRepository(db)

    if convoy_repository.get_by_convoy_id(convoy_id) is None:
        raise HTTPException(status_code=404, detail="Convoy not found")

    member = member_repository.get_member(convoy_id, vehicle_id)

    if member is None or member.status != "active":
        raise HTTPException(status_code=404, detail="Active convoy membership not found")

    if convoy_repository.get_by_convoy_id(convoy_id).leader_vehicle_id == vehicle_id:
        convoy = convoy_repository.get_by_convoy_id(convoy_id)
        convoy_repository.update_leader(convoy, None)

    member_repository.remove_member(member)
    db.commit()
    db.refresh(member)

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=ConvoyMemberOut.model_validate(member),
    )


@router.post(
    "/{convoy_id}/leader",
    response_model=APIResponse[ConvoyOut],
)
def assign_leader(
    convoy_id: str,
    payload: LeaderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CONVOY_LEADER_ASSIGN)),
):
    convoy_repository = ConvoyRepository(db)
    member_repository = ConvoyMemberRepository(db)
    vehicle_repository = VehicleRepository(db)

    convoy = convoy_repository.get_by_convoy_id(convoy_id)

    if convoy is None:
        raise HTTPException(status_code=404, detail="Convoy not found")

    if vehicle_repository.get_by_vehicle_id(payload.vehicle_id) is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    member = member_repository.get_member(convoy_id, payload.vehicle_id)

    if member is None or member.status != "active":
        raise HTTPException(
            status_code=409,
            detail="Leader must be an active convoy member",
        )

    active_members = member_repository.list_members(
        convoy_id,
        active_only=True,
    )

    for active_member in active_members:
        active_member.role = (
            "LEADER"
            if active_member.vehicle_id == payload.vehicle_id
            else "FOLLOWER"
        )

    convoy_repository.update_leader(convoy, payload.vehicle_id)
    db.commit()
    db.refresh(convoy)

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=ConvoyOut.model_validate(convoy),
    )
