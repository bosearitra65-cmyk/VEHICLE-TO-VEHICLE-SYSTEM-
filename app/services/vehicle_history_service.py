from datetime import datetime

from sqlalchemy.orm import Session

from app.database.repositories.vehicle_history_repository import VehicleHistoryRepository
from app.models.vehicle_history import VehicleHistory
from app.models.vehicle_state import VehicleState


def create_vehicle_history(
    db: Session,
    state: VehicleState,
) -> VehicleHistory:
    repository = VehicleHistoryRepository(db)

    return repository.create(
        vehicle_id=state.vehicle_id,
        sequence_number=state.sequence_number,
        timestamp=state.timestamp,
        latitude=state.latitude,
        longitude=state.longitude,
        speed=state.speed,
        heading=state.heading,
        communication_status=state.communication_status,
        device_id=state.device_id,
        boot_id=state.boot_id,
        gps_fix=state.gps_fix,
        satellites=state.satellites,
        hdop=state.hdop,
        gps_source=state.gps_source,
        transport=state.transport,
        convoy_id=state.convoy_id,
        role=state.role,
    )

def get_vehicle_history(
    db: Session,
    vehicle_id: str,
) -> list[VehicleHistory]:
    repository = VehicleHistoryRepository(db)
    return repository.list_by_vehicle(vehicle_id)


def get_vehicle_history_by_time(
    db: Session,
    vehicle_id: str,
    start_time: datetime,
    end_time: datetime,
) -> list[VehicleHistory]:
    repository = VehicleHistoryRepository(db)
    return repository.list_by_vehicle_and_time(
        vehicle_id=vehicle_id,
        start_time=start_time,
        end_time=end_time,
    )


def get_latest_vehicle_history(
    db: Session,
    vehicle_id: str,
) -> VehicleHistory | None:
    repository = VehicleHistoryRepository(db)
    return repository.get_latest(vehicle_id)
