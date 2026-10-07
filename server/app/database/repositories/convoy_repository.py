from sqlalchemy.orm import Session

from app.models.convoy import Convoy


class ConvoyRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        convoy_id: str,
        name: str,
        status: str,
        leader_vehicle_id: str | None = None,
        journey_id: str | None = None,
        route_id: str | None = None,
    ) -> Convoy:
        convoy = Convoy(
            convoy_id=convoy_id,
            name=name,
            status=status,
            leader_vehicle_id=leader_vehicle_id,
            journey_id=journey_id,
            route_id=route_id,
        )

        self.db.add(convoy)
        self.db.flush()
        self.db.refresh(convoy)

        return convoy

    def get_by_convoy_id(self, convoy_id: str) -> Convoy | None:
        return (
            self.db.query(Convoy)
            .filter(Convoy.convoy_id == convoy_id)
            .first()
        )

    def list_all(self) -> list[Convoy]:
        return (
            self.db.query(Convoy)
            .order_by(Convoy.id.asc())
            .all()
        )

    def update_status(
        self,
        convoy: Convoy,
        status: str,
    ) -> Convoy:
        convoy.status = status

        self.db.flush()
        self.db.refresh(convoy)

        return convoy

    def update_leader(
        self,
        convoy: Convoy,
        leader_vehicle_id: str | None,
    ) -> Convoy:
        convoy.leader_vehicle_id = leader_vehicle_id

        self.db.flush()
        self.db.refresh(convoy)

        return convoy
