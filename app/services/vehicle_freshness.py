from sqlalchemy.orm import Session

from app.database.repositories.vehicle_state_repository import VehicleStateRepository
from app.services.freshness import calculate_age_seconds, is_fresh


def get_vehicle_freshness(
    db: Session,
    vehicle_id: str,
    freshness_threshold_seconds: int = 10,
) -> dict | None:
    repository = VehicleStateRepository(db)

    state = repository.get_by_vehicle_id(vehicle_id)

    if state is None:
        return None

    age_seconds = calculate_age_seconds(state.timestamp)

    return {
        "vehicle_id": vehicle_id,
        "sequence_number": state.sequence_number,
        "timestamp": state.timestamp,
        "age_seconds": age_seconds,
        "is_fresh": is_fresh(
            state.timestamp,
            freshness_threshold_seconds,
        ),
    }
