from collections.abc import Generator
from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.authorization import has_permission, has_resource_access
from app.auth.permissions import Permission
from app.database.repositories.user_repository import UserRepository
from app.database.repositories.vehicle_repository import VehicleRepository
from app.database.repositories.user_resource_access_repository import (
    UserResourceAccessRepository,
)
from app.database.session import SessionLocal
from app.models.user import User
from app.schemas.vehicles import VehicleStateIn
from app.services.device_auth import DeviceAuthenticationError, authenticate_device
from app.services.firebase_auth import (
    FirebaseAuthenticationError,
    verify_firebase_token,
)


security = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication is required",
        )

    try:
        decoded_token = verify_firebase_token(credentials.credentials)
    except FirebaseAuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    firebase_uid = decoded_token.get("uid")

    if not firebase_uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase token does not contain a user ID",
        )

    user = UserRepository(db).get_by_firebase_uid(firebase_uid)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated user is not registered",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


def require_permission(
    permission: Permission | str,
) -> Callable:
    def permission_dependency(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return current_user

    return permission_dependency


def require_resource_access(
    permission: Permission | str,
    resource_type: str,
    resource_id_parameter: str,
) -> Callable:
    def resource_access_dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        resource_id = request.path_params.get(resource_id_parameter)

        if resource_id is None or not str(resource_id).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Resource identifier is required",
            )

        repository = UserResourceAccessRepository(db)

        allowed = has_resource_access(
            user=current_user,
            permission=permission,
            resource_type=resource_type,
            resource_id=str(resource_id),
            resource_access_checker=repository.has_access,
        )

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient resource access",
            )

        return current_user

    return resource_access_dependency


from dataclasses import dataclass


@dataclass(frozen=True)
class AuthenticatedDevice:
    vehicle_id: str
    device_id: str


def require_device_auth(
    request: Request,
    payload: VehicleStateIn,
    db: Session = Depends(get_db),
) -> AuthenticatedDevice | None:
    vehicle = VehicleRepository(db).get_by_vehicle_id(payload.vehicle_id)
    if vehicle is None:
        return None

    device_id = request.headers.get("X-Device-ID")
    device_key = request.headers.get("X-Device-Key")

    if not vehicle.device_auth_enabled and not device_id and not device_key:
        return None

    if not device_id or not device_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device authentication is required for this vehicle",
        )

    try:
        authenticated = authenticate_device(db, device_id=device_id, secret=device_key)
    except DeviceAuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
        ) from exc

    return AuthenticatedDevice(
        vehicle_id=authenticated.vehicle_id,
        device_id=authenticated.device_id or device_id,
    )
