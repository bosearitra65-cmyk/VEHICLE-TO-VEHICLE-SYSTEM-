from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user, require_permission
from app.auth.permissions import Permission
from app.auth.roles import UserRole, is_valid_role
from app.database.repositories.user_repository import UserRepository
from app.database.repositories.user_resource_access_repository import (
    UserResourceAccessRepository,
)
from app.database.repositories.vehicle_repository import VehicleRepository
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.users import (
    UserAccessCreate,
    UserAccessOut,
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.utils.identifiers import generate_request_id


router = APIRouter(
    prefix="/users",
    tags=["users"],
)


RESOURCE_PERMISSIONS: dict[str, frozenset[str]] = {
    "vehicle": frozenset(
        {
            Permission.VEHICLE_VIEW.value,
            Permission.VEHICLE_MANAGE.value,
        }
    ),
    "convoy": frozenset(
        {
            Permission.CONVOY_VIEW.value,
            Permission.CONVOY_MANAGE.value,
            Permission.CONVOY_LEADER_ASSIGN.value,
        }
    ),
    "journey": frozenset(
        {
            Permission.JOURNEY_VIEW.value,
            Permission.JOURNEY_MANAGE.value,
        }
    ),
    "route": frozenset(
        {
            Permission.ROUTE_VIEW.value,
            Permission.ROUTE_MANAGE.value,
        }
    ),
}


def _administrator_protection(
    current_user: User,
    target_user: User,
) -> None:
    if (
        target_user.role == UserRole.ADMINISTRATOR.value
        and target_user.id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="An Administrator cannot modify another Administrator's authority",
        )


def _validate_role_for_creation(role: str) -> None:
    if not is_valid_role(role):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user role: {role}",
        )

    if role == UserRole.ADMINISTRATOR.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Creation of another Administrator is not permitted through this API",
        )


def _validate_role_for_update(
    current_user: User,
    target_user: User,
    role: str | None,
) -> None:
    if role is None:
        return

    if not is_valid_role(role):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user role: {role}",
        )

    if (
        role == UserRole.ADMINISTRATOR.value
        and target_user.id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="An Administrator cannot grant Administrator authority to another user",
        )


def _validate_permission(permission: str) -> None:
    try:
        Permission(permission)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown permission: {permission}",
        ) from exc


def _validate_resource_permission(
    resource_type: str,
    permission: str,
) -> None:
    allowed_permissions = RESOURCE_PERMISSIONS.get(resource_type)

    if allowed_permissions is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported resource type: {resource_type}",
        )

    if permission not in allowed_permissions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Permission '{permission}' is not valid for "
                f"resource type '{resource_type}'"
            ),
        )


def _validate_resource_exists(
    db: Session,
    resource_type: str,
    resource_id: str,
) -> None:
    if resource_type == "vehicle":
        vehicle = VehicleRepository(db).get_by_vehicle_id(resource_id)

        if vehicle is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vehicle not found: {resource_id}",
            )
        return


@router.get(
    "/me",
    response_model=APIResponse[UserOut],
    status_code=status.HTTP_200_OK,
)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=UserOut.model_validate(
            current_user,
            from_attributes=True,
        ),
    )


@router.get(
    "",
    response_model=APIResponse[list[UserOut]],
    status_code=status.HTTP_200_OK,
)
def list_users(
    current_user: User = Depends(
        require_permission(Permission.USER_MANAGE)
    ),
    db: Session = Depends(get_db),
):
    users = UserRepository(db).get_all()

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=[
            UserOut.model_validate(
                user,
                from_attributes=True,
            )
            for user in users
        ],
    )


@router.get(
    "/{user_id}",
    response_model=APIResponse[UserOut],
    status_code=status.HTTP_200_OK,
)
def get_user(
    user_id: int,
    current_user: User = Depends(
        require_permission(Permission.USER_MANAGE)
    ),
    db: Session = Depends(get_db),
):
    repository = UserRepository(db)
    user = repository.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=UserOut.model_validate(
            user,
            from_attributes=True,
        ),
    )


@router.post(
    "",
    response_model=APIResponse[UserOut],
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    payload: UserCreate,
    current_user: User = Depends(
        require_permission(Permission.USER_MANAGE)
    ),
    db: Session = Depends(get_db),
):
    _validate_role_for_creation(payload.role)

    repository = UserRepository(db)

    if repository.get_by_email(payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    if (
        payload.firebase_uid
        and repository.get_by_firebase_uid(payload.firebase_uid)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this Firebase UID already exists",
        )

    try:
        user = repository.create(
            firebase_uid=payload.firebase_uid,
            email=payload.email,
            role=payload.role,
            is_active=payload.is_active,
        )
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User could not be created because of a uniqueness conflict",
        ) from exc

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=UserOut.model_validate(
            user,
            from_attributes=True,
        ),
    )


@router.patch(
    "/{user_id}",
    response_model=APIResponse[UserOut],
    status_code=status.HTTP_200_OK,
)
def update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: User = Depends(
        require_permission(Permission.USER_MANAGE)
    ),
    db: Session = Depends(get_db),
):
    repository = UserRepository(db)
    user = repository.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    _administrator_protection(current_user, user)

    fields = payload.model_dump(exclude_unset=True)

    if "role" in fields:
        _validate_role_for_update(
            current_user,
            user,
            fields["role"],
        )

    if "email" in fields:
        existing = repository.get_by_email(fields["email"])

        if existing is not None and existing.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists",
            )

    try:
        user = repository.update(user, **fields)
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User could not be updated because of a uniqueness conflict",
        ) from exc

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=UserOut.model_validate(
            user,
            from_attributes=True,
        ),
    )


@router.get(
    "/{user_id}/access",
    response_model=APIResponse[list[UserAccessOut]],
    status_code=status.HTTP_200_OK,
)
def list_user_access(
    user_id: int,
    current_user: User = Depends(
        require_permission(Permission.ACCESS_MANAGE)
    ),
    db: Session = Depends(get_db),
):
    user_repository = UserRepository(db)
    target_user = user_repository.get_by_id(user_id)

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    access_repository = UserResourceAccessRepository(db)

    records = access_repository.get_for_user(user_id)

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=[
            UserAccessOut.model_validate(
                record,
                from_attributes=True,
            )
            for record in records
        ],
    )


@router.post(
    "/{user_id}/access",
    response_model=APIResponse[UserAccessOut],
    status_code=status.HTTP_201_CREATED,
)
def grant_user_access(
    user_id: int,
    payload: UserAccessCreate,
    current_user: User = Depends(
        require_permission(Permission.ACCESS_MANAGE)
    ),
    db: Session = Depends(get_db),
):
    user_repository = UserRepository(db)
    target_user = user_repository.get_by_id(user_id)

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    _administrator_protection(current_user, target_user)

    _validate_permission(payload.permission)
    _validate_resource_permission(
        payload.resource_type,
        payload.permission,
    )
    _validate_resource_exists(
        db,
        payload.resource_type,
        payload.resource_id,
    )

    access_repository = UserResourceAccessRepository(db)

    if access_repository.has_access(
        user_id,
        payload.resource_type,
        payload.resource_id,
        payload.permission,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This resource permission already exists",
        )

    try:
        record = access_repository.create(
            user_id=user_id,
            resource_type=payload.resource_type,
            resource_id=payload.resource_id,
            permission=payload.permission,
            created_by=current_user.id,
        )

        db.commit()
        db.refresh(record)

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to create the requested access record",
        ) from exc

    except Exception:
        db.rollback()
        raise

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=UserAccessOut.model_validate(
            record,
            from_attributes=True,
        ),
    )


@router.delete(
    "/{user_id}/access",
    response_model=APIResponse[dict[str, bool]],
    status_code=status.HTTP_200_OK,
)
def revoke_user_access(
    user_id: int,
    resource_type: str,
    resource_id: str,
    permission: str,
    current_user: User = Depends(
        require_permission(Permission.ACCESS_MANAGE)
    ),
    db: Session = Depends(get_db),
):
    user_repository = UserRepository(db)
    target_user = user_repository.get_by_id(user_id)

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    _administrator_protection(current_user, target_user)

    _validate_permission(permission)
    _validate_resource_permission(
        resource_type,
        permission,
    )

    access_repository = UserResourceAccessRepository(db)

    try:
        deleted = access_repository.delete(
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            permission=permission,
        )

        if not deleted:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource permission not found",
            )

        db.commit()

    except HTTPException:
        raise

    except Exception:
        db.rollback()
        raise

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data={"deleted": True},
    )
