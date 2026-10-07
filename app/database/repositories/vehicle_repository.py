from sqlalchemy.orm import Session

from app.models.vehicle import Vehicle


class VehicleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_vehicle_id(self, vehicle_id: str) -> Vehicle | None:
        return (
            self.db.query(Vehicle)
            .filter(Vehicle.vehicle_id == vehicle_id)
            .first()
        )

    def get_by_device_id(self, device_id: str) -> Vehicle | None:
        return (
            self.db.query(Vehicle)
            .filter(Vehicle.device_id == device_id)
            .first()
        )

    def list_all(self) -> list[Vehicle]:
        return self.db.query(Vehicle).order_by(Vehicle.id.asc()).all()

    def create(
        self,
        vehicle_id: str,
        device_id: str | None = None,
        name: str | None = None,
    ) -> Vehicle:
        vehicle = Vehicle(
            vehicle_id=vehicle_id,
            device_id=device_id,
            name=name,
            is_active=True,
        )
        self.db.add(vehicle)
        self.db.flush()
        self.db.refresh(vehicle)
        return vehicle

    def update(
        self,
        vehicle: Vehicle,
        device_id: str | None = None,
        name: str | None = None,
        is_active: bool | None = None,
    ) -> Vehicle:
        if device_id is not None:
            vehicle.device_id = device_id
        if name is not None:
            vehicle.name = name
        if is_active is not None:
            vehicle.is_active = is_active

        self.db.flush()
        self.db.refresh(vehicle)
        return vehicle
