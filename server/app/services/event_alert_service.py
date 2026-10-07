from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.event import Event
from app.services.alert_rules import should_create_alert
from app.services.alert_service import create_alert


def process_event_for_alert(
    db: Session,
    event: Event,
) -> Alert | None:
    if not should_create_alert(event):
        return None

    return create_alert(
        db=db,
        vehicle_id=event.vehicle_id,
        alert_type=event.event_type,
        severity=event.severity,
        message=event.message,
        source_event_id=event.id,
    )