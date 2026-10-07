from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database.repositories.vehicle_session_repository import VehicleSessionRepository
from app.models.vehicle_session import VehicleSession


def get_or_create_vehicle_session(
    db: Session,
    vehicle_id: str,
    boot_id: str,
) -> VehicleSession:
    repository = VehicleSessionRepository(db)

    session = repository.get_active_by_vehicle_and_boot(
        vehicle_id=vehicle_id,
        boot_id=boot_id,
    )

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if session is not None:
        return repository.update_last_seen(
            session=session,
            last_seen_at=now,
        )

    active_sessions = repository.list_active_by_vehicle(vehicle_id)

    for active_session in active_sessions:
        repository.deactivate(active_session)

    return repository.create(
        vehicle_id=vehicle_id,
        boot_id=boot_id,
        started_at=now,
        last_seen_at=now,
    )
