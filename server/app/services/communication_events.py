from sqlalchemy.orm import Session

from app.config.constants import (
    EVENT_COMMUNICATION_LOSS,
    EVENT_COMMUNICATION_RECOVERY,
)
from app.services.communication_state import (
    determine_communication_transition,
)
from app.services.event_service import create_event


def process_communication_transition(
    db: Session,
    vehicle_id: str,
    previous_availability: str | None,
    current_availability: str,
    sequence_number: int | None = None,
):
    transition = determine_communication_transition(
        previous_availability=previous_availability,
        current_availability=current_availability,
    )

    if transition is None:
        return None

    if transition == "communication_loss":
        return create_event(
            db=db,
            vehicle_id=vehicle_id,
            event_type=EVENT_COMMUNICATION_LOSS,
            severity="critical",
            message="Vehicle communication loss detected",
            sequence_number=sequence_number,
        )

    if transition == "communication_recovery":
        return create_event(
            db=db,
            vehicle_id=vehicle_id,
            event_type=EVENT_COMMUNICATION_RECOVERY,
            severity="info",
            message="Vehicle communication recovered",
            sequence_number=sequence_number,
        )

    return None