from sqlalchemy.orm import Session

from app.database.repositories.route_repository import RouteRepository
from app.models.route import Route


class RouteService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = RouteRepository(db)

    def create_route(
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
        existing = self.repository.get_by_route_id(route_id)

        if existing is not None:
            raise ValueError("Route already exists")

        return self.repository.create(
            route_id=route_id,
            origin=origin,
            destination=destination,
            geometry=geometry,
            distance=distance,
            estimated_duration=estimated_duration,
            created_by=created_by,
            version=version,
        )

    def get_route(
        self,
        route_id: str,
    ) -> Route | None:
        return self.repository.get_by_route_id(route_id)

    def list_routes(self) -> list[Route]:
        return self.repository.list_all()

    def update_route(
        self,
        route_id: str,
        geometry: str,
        distance: float | None = None,
        estimated_duration: int | None = None,
    ) -> Route:
        route = self.repository.get_by_route_id(route_id)

        if route is None:
            raise ValueError("Route not found")

        return self.repository.update_version(
            route=route,
            geometry=geometry,
            distance=distance,
            estimated_duration=estimated_duration,
        )
