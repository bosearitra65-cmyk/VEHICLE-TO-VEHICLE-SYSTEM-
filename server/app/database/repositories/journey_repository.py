from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.journey import Journey


class JourneyRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        journey_id: str,
        convoy_id: str,
        origin: str,
        destination: str,
        status: str,
        route_id: str | None = None,
        planned_start_at: datetime | None = None,
        created_by: str | None = None,
    ) -> Journey:
        journey = Journey(
            journey_id=journey_id,
            convoy_id=convoy_id,
            origin=origin,
            destination=destination,
            route_id=route_id,
            status=status,
            planned_start_at=planned_start_at,
            created_by=created_by,
        )
        self.db.add(journey)
        self.db.flush()
        self.db.refresh(journey)
        return journey

    def get_by_journey_id(self, journey_id: str) -> Journey | None:
        return (
            self.db.query(Journey)
            .filter(Journey.journey_id == journey_id)
            .first()
        )

    def list_all(self) -> list[Journey]:
        return self.db.query(Journey).order_by(Journey.id.asc()).all()

    def update(
        self,
        journey: Journey,
        origin: str | None = None,
        destination: str | None = None,
        planned_start_at: datetime | None = None,
    ) -> Journey:
        if origin is not None:
            journey.origin = origin
        if destination is not None:
            journey.destination = destination
        if planned_start_at is not None:
            journey.planned_start_at = planned_start_at

        self.db.flush()
        self.db.refresh(journey)
        return journey

    def assign_route(
        self,
        journey: Journey,
        route_id: str,
    ) -> Journey:
        journey.route_id = route_id
        self.db.flush()
        self.db.refresh(journey)
        return journey

    def update_status(
        self,
        journey: Journey,
        status: str,
    ) -> Journey:
        journey.status = status
        self.db.flush()
        self.db.refresh(journey)
        return journey

    def start(self, journey: Journey) -> Journey:
        journey.status = "active"
        journey.actual_start_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.db.flush()
        self.db.refresh(journey)
        return journey

    def complete(self, journey: Journey) -> Journey:
        journey.status = "completed"
        journey.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.db.flush()
        self.db.refresh(journey)
        return journey
