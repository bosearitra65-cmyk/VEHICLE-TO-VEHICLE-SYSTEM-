from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_permission
from app.auth.permissions import Permission
from app.database.repositories.event_repository import EventRepository
from app.database.repositories.vehicle_repository import VehicleRepository
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.operational import EventOut
from app.utils.identifiers import generate_request_id


router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=APIResponse[list[EventOut]])
def list_events(
    vehicle_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EVENTS_VIEW)),
):
    repository = EventRepository(db)

    if vehicle_id is not None:
        if VehicleRepository(db).get_by_vehicle_id(vehicle_id) is None:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        events = repository.list_by_vehicle(vehicle_id)
    else:
        events = repository.list_all()

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=[EventOut.model_validate(item) for item in events],
    )


@router.get(
    "/{event_id}",
    response_model=APIResponse[EventOut],
)
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EVENTS_VIEW)),
):
    event = EventRepository(db).get_by_id(event_id)

    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=EventOut.model_validate(event),
    )
