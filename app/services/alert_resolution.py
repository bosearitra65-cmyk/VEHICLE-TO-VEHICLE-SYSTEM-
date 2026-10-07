from sqlalchemy.orm import Session

from app.database.repositories.alert_repository import AlertRepository


def resolve_communication_alerts(
    db: Session,
    vehicle_id: str,
) -> int:
    repository = AlertRepository(db)

    alerts = repository.list_active_by_vehicle(vehicle_id)

    communication_alerts = [
        alert
        for alert in alerts
        if alert.alert_type == "communication_loss"
    ]

    for alert in communication_alerts:
        repository.resolve(alert)

    return len(communication_alerts)
