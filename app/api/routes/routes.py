from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_permission
from app.auth.permissions import Permission
from app.database.repositories.route_repository import RouteRepository
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.operational import RouteCalculate, RouteCreate, RouteOut
from app.utils.identifiers import generate_request_id


router = APIRouter(prefix="/routes", tags=["routes"])


@router.get("", response_model=APIResponse[list[RouteOut]])
def list_routes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ROUTE_VIEW)),
):
    routes = RouteRepository(db).list_all()

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=[RouteOut.model_validate(item) for item in routes],
    )


@router.post(
    "",
    response_model=APIResponse[RouteOut],
    status_code=status.HTTP_201_CREATED,
)
def create_route(
    payload: RouteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ROUTE_MANAGE)),
):
    repository = RouteRepository(db)

    if repository.get_by_route_id(payload.route_id):
        raise HTTPException(status_code=409, detail="Route already exists")

    route = repository.create(
        route_id=payload.route_id,
        origin=payload.origin,
        destination=payload.destination,
        geometry=payload.geometry,
        distance=payload.distance,
        estimated_duration=payload.estimated_duration,
        created_by=current_user.firebase_uid,
    )

    db.commit()
    db.refresh(route)

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=RouteOut.model_validate(route),
    )


@router.get(
    "/{route_id}",
    response_model=APIResponse[RouteOut],
)
def get_route(
    route_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ROUTE_VIEW)),
):
    route = RouteRepository(db).get_by_route_id(route_id)

    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=RouteOut.model_validate(route),
    )


@router.post(
    "/calculate",
    response_model=APIResponse[dict],
)
def calculate_route(
    payload: RouteCalculate,
    current_user: User = Depends(require_permission(Permission.ROUTE_MANAGE)),
):
    raise HTTPException(
        status_code=501,
        detail="Route calculation provider is not configured",
    )
