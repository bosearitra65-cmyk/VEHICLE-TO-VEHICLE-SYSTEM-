from datetime import datetime

from sqlalchemy.orm import Session

from app.models.route_stop import RouteStop


class RouteStopRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        stop_id: str,
        route_id: str,
        sequence: int,
        name: str,
        latitude: float,
        longitude: float,
        planned_arrival: datetime | None = None,
        planned_departure: datetime | None = None,
        status: str = "planned",
    ) -> RouteStop:
        stop = RouteStop(
            stop_id=stop_id,
            route_id=route_id,
            sequence=sequence,
            name=name,
            latitude=latitude,
            longitude=longitude,
            planned_arrival=planned_arrival,
            planned_departure=planned_departure,
            status=status,
        )

        self.db.add(stop)
        self.db.flush()
        self.db.refresh(stop)

        return stop

    def get_by_stop_id(self, stop_id: str) -> RouteStop | None:
        return (
            self.db.query(RouteStop)
            .filter(RouteStop.stop_id == stop_id)
            .first()
        )

    def get_by_route_and_sequence(
        self,
        route_id: str,
        sequence: int,
    ) -> RouteStop | None:
        return (
            self.db.query(RouteStop)
            .filter(
                RouteStop.route_id == route_id,
                RouteStop.sequence == sequence,
            )
            .first()
        )

    def list_by_route(self, route_id: str) -> list[RouteStop]:
        return (
            self.db.query(RouteStop)
            .filter(RouteStop.route_id == route_id)
            .order_by(RouteStop.sequence.asc())
            .all()
        )
