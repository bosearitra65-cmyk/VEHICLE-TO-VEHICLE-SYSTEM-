from sqlalchemy.orm import Session

from app.models.event import Event


class EventRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        vehicle_id: str,
        event_type: str,
        severity: str,
        message: str,
        sequence_number: int | None = None,
    ) -> Event:
        event = Event(
            vehicle_id=vehicle_id,
            event_type=event_type,
            severity=severity,
            sequence_number=sequence_number,
            message=message,
        )

        self.db.add(event)
        self.db.flush()
        self.db.refresh(event)

        return event

    def get_by_id(
        self,
        event_id: int,
    ) -> Event | None:
        return (
            self.db.query(Event)
            .filter(Event.id == event_id)
            .first()
        )

    def list_by_vehicle(
        self,
        vehicle_id: str,
    ) -> list[Event]:
        return (
            self.db.query(Event)
            .filter(Event.vehicle_id == vehicle_id)
            .order_by(Event.id.asc())
            .all()
        )

    def list_all(self) -> list[Event]:
        return (
            self.db.query(Event)
            .order_by(Event.id.asc())
            .all()
        )
