from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_permission
from app.auth.permissions import Permission
from app.database.repositories.convoy_repository import ConvoyRepository
from app.database.repositories.journey_repository import JourneyRepository
from app.database.repositories.route_repository import RouteRepository
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.operational import JourneyCreate, JourneyOut, JourneyUpdate
from app.utils.identifiers import generate_request_id


router = APIRouter(prefix="/journeys", tags=["journeys"])


@router.get("", response_model=APIResponse[list[JourneyOut]])
def list_journeys(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.JOURNEY_VIEW)),
):
    journeys = JourneyRepository(db).list_all()

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=[JourneyOut.model_validate(item) for item in journeys],
    )


@router.post(
    "",
    response_model=APIResponse[JourneyOut],
    status_code=status.HTTP_201_CREATED,
)
def create_journey(
    payload: JourneyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.JOURNEY_MANAGE)),
):
    repository = JourneyRepository(db)

    if repository.get_by_journey_id(payload.journey_id):
        raise HTTPException(status_code=409, detail="Journey already exists")

    if ConvoyRepository(db).get_by_convoy_id(payload.convoy_id) is None:
        raise HTTPException(status_code=404, detail="Convoy not found")

    if payload.route_id is not None and RouteRepository(db).get_by_route_id(payload.route_id) is None:
        raise HTTPException(status_code=404, detail="Route not found")

    journey = repository.create(
        journey_id=payload.journey_id,
        convoy_id=payload.convoy_id,
        origin=payload.origin,
        destination=payload.destination,
        route_id=payload.route_id,
        status="planned",
        planned_start_at=payload.planned_start_at,
        created_by=current_user.firebase_uid,
    )

    db.commit()
    db.refresh(journey)

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=JourneyOut.model_validate(journey),
    )


@router.get(
    "/{journey_id}",
    response_model=APIResponse[JourneyOut],
)
def get_journey(
    journey_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.JOURNEY_VIEW)),
):
    journey = JourneyRepository(db).get_by_journey_id(journey_id)

    if journey is None:
        raise HTTPException(status_code=404, detail="Journey not found")

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=JourneyOut.model_validate(journey),
    )


@router.patch(
    "/{journey_id}",
    response_model=APIResponse[JourneyOut],
)
def update_journey(
    journey_id: str,
    payload: JourneyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.JOURNEY_MANAGE)),
):
    repository = JourneyRepository(db)
    journey = repository.get_by_journey_id(journey_id)

    if journey is None:
        raise HTTPException(status_code=404, detail="Journey not found")

    if journey.status not in {"planned"}:
        raise HTTPException(
            status_code=409,
            detail="Only planned journeys can be edited",
        )

    journey = repository.update(
        journey,
        origin=payload.origin,
        destination=payload.destination,
        planned_start_at=payload.planned_start_at,
    )

    db.commit()
    db.refresh(journey)

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=JourneyOut.model_validate(journey),
    )


@router.post(
    "/{journey_id}/start",
    response_model=APIResponse[JourneyOut],
)
def start_journey(
    journey_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.JOURNEY_MANAGE)),
):
    repository = JourneyRepository(db)
    journey = repository.get_by_journey_id(journey_id)

    if journey is None:
        raise HTTPException(status_code=404, detail="Journey not found")

    if journey.status != "planned":
        raise HTTPException(status_code=409, detail="Journey cannot be started from its current state")

    repository.start(journey)
    db.commit()
    db.refresh(journey)

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=JourneyOut.model_validate(journey),
    )


@router.post(
    "/{journey_id}/pause",
    response_model=APIResponse[JourneyOut],
)
def pause_journey(
    journey_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.JOURNEY_MANAGE)),
):
    repository = JourneyRepository(db)
    journey = repository.get_by_journey_id(journey_id)

    if journey is None:
        raise HTTPException(status_code=404, detail="Journey not found")

    if journey.status != "active":
        raise HTTPException(status_code=409, detail="Only active journeys can be paused")

    repository.update_status(journey, "paused")
    db.commit()
    db.refresh(journey)

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=JourneyOut.model_validate(journey),
    )


@router.post(
    "/{journey_id}/resume",
    response_model=APIResponse[JourneyOut],
)
def resume_journey(
    journey_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.JOURNEY_MANAGE)),
):
    repository = JourneyRepository(db)
    journey = repository.get_by_journey_id(journey_id)

    if journey is None:
        raise HTTPException(status_code=404, detail="Journey not found")

    if journey.status != "paused":
        raise HTTPException(status_code=409, detail="Only paused journeys can be resumed")

    repository.update_status(journey, "active")
    db.commit()
    db.refresh(journey)

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=JourneyOut.model_validate(journey),
    )


@router.post(
    "/{journey_id}/complete",
    response_model=APIResponse[JourneyOut],
)
def complete_journey(
    journey_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.JOURNEY_MANAGE)),
):
    repository = JourneyRepository(db)
    journey = repository.get_by_journey_id(journey_id)

    if journey is None:
        raise HTTPException(status_code=404, detail="Journey not found")

    if journey.status not in {"active", "paused"}:
        raise HTTPException(
            status_code=409,
            detail="Only active or paused journeys can be completed",
        )

    repository.complete(journey)
    db.commit()
    db.refresh(journey)

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=JourneyOut.model_validate(journey),
    )


@router.post(
    "/{journey_id}/abort",
    response_model=APIResponse[JourneyOut],
)
def abort_journey(
    journey_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.JOURNEY_MANAGE)),
):
    repository = JourneyRepository(db)
    journey = repository.get_by_journey_id(journey_id)

    if journey is None:
        raise HTTPException(status_code=404, detail="Journey not found")

    if journey.status not in {"planned", "active", "paused"}:
        raise HTTPException(status_code=409, detail="Journey cannot be aborted from its current state")

    repository.update_status(journey, "aborted")
    db.commit()
    db.refresh(journey)

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=JourneyOut.model_validate(journey),
    )


@router.post(
    "/{journey_id}/route/{route_id}",
    response_model=APIResponse[JourneyOut],
)
def assign_route(
    journey_id: str,
    route_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.JOURNEY_MANAGE)),
):
    journey_repository = JourneyRepository(db)

    journey = journey_repository.get_by_journey_id(journey_id)

    if journey is None:
        raise HTTPException(status_code=404, detail="Journey not found")

    if RouteRepository(db).get_by_route_id(route_id) is None:
        raise HTTPException(status_code=404, detail="Route not found")

    if journey.status not in {"planned"}:
        raise HTTPException(
            status_code=409,
            detail="Route can only be assigned to a planned journey",
        )

    journey_repository.assign_route(journey, route_id)
    db.commit()
    db.refresh(journey)

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=JourneyOut.model_validate(journey),
    )
