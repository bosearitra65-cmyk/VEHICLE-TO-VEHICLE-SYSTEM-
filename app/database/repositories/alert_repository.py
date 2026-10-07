from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.alert import Alert


class AlertRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        vehicle_id: str,
        alert_type: str,
        severity: str,
        message: str,
        source_event_id: int | None = None,
    ) -> Alert:
        alert = Alert(
            vehicle_id=vehicle_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            source_event_id=source_event_id,
        )

        self.db.add(alert)
        self.db.flush()
        self.db.refresh(alert)

        return alert

    def get_by_id(
        self,
        alert_id: int,
    ) -> Alert | None:
        return (
            self.db.query(Alert)
            .filter(Alert.id == alert_id)
            .first()
        )

    def list_by_vehicle(
        self,
        vehicle_id: str,
    ) -> list[Alert]:
        return (
            self.db.query(Alert)
            .filter(Alert.vehicle_id == vehicle_id)
            .order_by(Alert.id.asc())
            .all()
        )

    def list_active_by_vehicle(
        self,
        vehicle_id: str,
    ) -> list[Alert]:
        return (
            self.db.query(Alert)
            .filter(
                Alert.vehicle_id == vehicle_id,
                Alert.is_active.is_(True),
            )
            .order_by(Alert.id.asc())
            .all()
        )

    def resolve(
        self,
        alert: Alert,
    ) -> Alert:
        alert.is_active = False
        alert.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)

        self.db.flush()
        self.db.refresh(alert)

        return alert
