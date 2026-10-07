from sqlalchemy.orm import Session

from app.database.repositories.event_repository import EventRepository
from app.models.event import Event
from app.realtime.publisher import publisher


def create_event(
    db: Session,
    vehicle_id: str,
    event_type: str,
    severity: str,
    message: str,
    sequence_number: int | None = None,
) -> Event:
    repository = EventRepository(db)

    event = repository.create(
        vehicle_id=vehicle_id,
        event_type=event_type,
        severity=severity,
        message=message,
        sequence_number=sequence_number,
    )

    publisher.publish_from_sync(
        "EVENT_CREATED",
        "event",
        str(event.id),
        {
            "event_id": event.id,
            "vehicle_id": event.vehicle_id,
            "event_type": event.event_type,
            "severity": event.severity,
            "message": event.message,
            "sequence_number": event.sequence_number,
        },
        version=int(event.id),
        vehicle_id=vehicle_id,
    )

    # Specialized realtime projections of authoritative events.
    # These do not create a second source of truth.
    specialized_type = None

    event_type_value = str(event.event_type or "").lower()

    if "communication_loss" in event_type_value:
        specialized_type = "VEHICLE_STATUS_CHANGED"

    elif (
        "communication_recovery" in event_type_value
        or "communication_restored" in event_type_value
    ):
        specialized_type = "VEHICLE_STATUS_CHANGED"

    elif "route_deviation_recovered" in event_type_value:
        specialized_type = "ROUTE_DEVIATION_CLEARED"

    elif "route_deviation" in event_type_value:
        specialized_type = "ROUTE_DEVIATION_DETECTED"

    elif "route_completed" in event_type_value:
        specialized_type = "ROUTE_UPDATED"

    if specialized_type is not None:
        publisher.publish_from_sync(
            specialized_type,
            "vehicle",
            str(event.vehicle_id),
            {
                "event_id": event.id,
                "vehicle_id": event.vehicle_id,
                "event_type": event.event_type,
                "severity": event.severity,
                "message": event.message,
                "sequence_number": event.sequence_number,
            },
            version=int(event.id),
            vehicle_id=event.vehicle_id,
        )

    return event
