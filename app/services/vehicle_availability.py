from sqlalchemy.orm import Session

from app.database.repositories.vehicle_state_repository import VehicleStateRepository
from app.services.availability import determine_availability
from app.services.freshness import calculate_age_seconds, is_fresh


def get_vehicle_availability(
    db: Session,
    vehicle_id: str,
    freshness_threshold_seconds: int = 10,
) -> dict | None:
    repository = VehicleStateRepository(db)

    state = repository.get_by_vehicle_id(vehicle_id)

    if state is None:
        return None

    age_seconds = calculate_age_seconds(state.timestamp)
    fresh = is_fresh(
        state.timestamp,
        freshness_threshold_seconds,
    )

    availability = determine_availability(
        is_fresh=fresh,
        communication_status=state.communication_status,
    )

    return {
        "vehicle_id": vehicle_id,
        "sequence_number": state.sequence_number,
        "age_seconds": age_seconds,
        "is_fresh": fresh,
        "reported_communication_status": state.communication_status,
        "availability": availability,
    }
