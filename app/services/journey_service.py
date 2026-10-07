from sqlalchemy.orm import Session

from app.database.repositories.journey_repository import JourneyRepository
from app.models.journey import Journey


class JourneyService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = JourneyRepository(db)

    def create_journey(
        self,
        journey_id: str,
        convoy_id: str,
        origin: str,
        destination: str,
        status: str,
        route_id: str | None = None,
        planned_start_at=None,
        created_by: str | None = None,
    ) -> Journey:
        existing = self.repository.get_by_journey_id(journey_id)

        if existing is not None:
            raise ValueError("Journey already exists")

        return self.repository.create(
            journey_id=journey_id,
            convoy_id=convoy_id,
            origin=origin,
            destination=destination,
            status=status,
            route_id=route_id,
            planned_start_at=planned_start_at,
            created_by=created_by,
        )

    def get_journey(
        self,
        journey_id: str,
    ) -> Journey | None:
        return self.repository.get_by_journey_id(journey_id)

    def list_journeys(self) -> list[Journey]:
        return self.repository.list_all()

    def update_status(
        self,
        journey_id: str,
        status: str,
    ) -> Journey:
        journey = self.repository.get_by_journey_id(journey_id)

        if journey is None:
            raise ValueError("Journey not found")

        return self.repository.update_status(
            journey=journey,
            status=status,
        )

    def start_journey(
        self,
        journey_id: str,
    ) -> Journey:
        journey = self.repository.get_by_journey_id(journey_id)

        if journey is None:
            raise ValueError("Journey not found")

        if journey.status != "planned":
            raise ValueError("Only a planned journey can be started")

        return self.repository.start(journey)

    def complete_journey(
        self,
        journey_id: str,
    ) -> Journey:
        journey = self.repository.get_by_journey_id(journey_id)

        if journey is None:
            raise ValueError("Journey not found")

        if journey.status != "active":
            raise ValueError("Only an active journey can be completed")

        return self.repository.complete(journey)
