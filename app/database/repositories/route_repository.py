from sqlalchemy.orm import Session

from app.models.route import Route


class RouteRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        route_id: str,
        origin: str,
        destination: str,
        geometry: str,
        distance: float | None = None,
        estimated_duration: int | None = None,
        created_by: str | None = None,
        version: int = 1,
    ) -> Route:
        route = Route(
            route_id=route_id,
            origin=origin,
            destination=destination,
            geometry=geometry,
            distance=distance,
            estimated_duration=estimated_duration,
            created_by=created_by,
            version=version,
        )

        self.db.add(route)
        self.db.flush()
        self.db.refresh(route)

        return route

    def get_by_route_id(self, route_id: str) -> Route | None:
        return (
            self.db.query(Route)
            .filter(Route.route_id == route_id)
            .first()
        )

    def list_all(self) -> list[Route]:
        return (
            self.db.query(Route)
            .order_by(Route.id.asc())
            .all()
        )

    def update_version(
        self,
        route: Route,
        geometry: str,
        distance: float | None = None,
        estimated_duration: int | None = None,
    ) -> Route:
        route.geometry = geometry
        route.distance = distance
        route.estimated_duration = estimated_duration
        route.version += 1

        self.db.flush()
        self.db.refresh(route)

        return route
