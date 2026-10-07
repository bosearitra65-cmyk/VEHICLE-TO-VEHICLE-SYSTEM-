from sqlalchemy.orm import Session

from app.database.repositories.vehicle_repository import VehicleRepository
from app.models.vehicle import Vehicle


class VehicleIdentityError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def validate_vehicle_identity(
    db: Session,
    vehicle_id: str,
    device_id: str | None = None,
) -> Vehicle:
    repository = VehicleRepository(db)

    vehicle = repository.get_by_vehicle_id(vehicle_id)

    if vehicle is None:
        raise VehicleIdentityError("Vehicle is not registered")

    if not vehicle.is_active:
        raise VehicleIdentityError("Vehicle is inactive")

    if device_id is not None and vehicle.device_id != device_id:
        raise VehicleIdentityError("Device does not match vehicle")

    return vehicle
