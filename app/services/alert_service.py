from sqlalchemy.orm import Session

from app.database.repositories.alert_repository import AlertRepository
from app.models.alert import Alert
from app.realtime.publisher import publisher


def create_alert(
    db: Session,
    vehicle_id: str,
    alert_type: str,
    severity: str,
    message: str,
    source_event_id: int | None = None,
) -> Alert:
    repository = AlertRepository(db)

    alert = repository.create(
        vehicle_id=vehicle_id,
        alert_type=alert_type,
        severity=severity,
        message=message,
        source_event_id=source_event_id,
    )

    publisher.publish_from_sync(
        "ALERT_CREATED",
        "alert",
        str(alert.id),
        {
            "alert_id": alert.id,
            "vehicle_id": alert.vehicle_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "message": alert.message,
            "source_event_id": alert.source_event_id,
        },
        version=int(alert.id),
        vehicle_id=vehicle_id,
    )

    return alert
