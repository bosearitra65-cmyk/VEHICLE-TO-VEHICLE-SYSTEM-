from sqlalchemy.orm import Session

from app.config.constants import COMMUNICATION_DISCONNECTED
from app.models.alert import Alert
from app.models.vehicle_state import VehicleState
from app.services.alert_service import create_alert
from app.services.availability import determine_availability
from app.services.event_service import create_event
from app.services.freshness import is_fresh


def monitor_vehicle_communications(
    db: Session,
    freshness_threshold_seconds: int = 10,
) -> list[dict]:
    states = db.query(VehicleState).all()
    results = []

    for state in states:
        fresh = is_fresh(
            state.timestamp,
            freshness_threshold_seconds,
        )

        availability = determine_availability(
            is_fresh=fresh,
            communication_status=state.communication_status,
        )

        result = {
            "vehicle_id": state.vehicle_id,
            "sequence_number": state.sequence_number,
            "is_fresh": fresh,
            "availability": availability,
            "communication_loss_detected": False,
            "alert_created": False,
        }

        if availability != COMMUNICATION_DISCONNECTED:
            results.append(result)
            continue

        existing_alert = (
            db.query(Alert)
            .filter(
                Alert.vehicle_id == state.vehicle_id,
                Alert.alert_type == "communication_loss",
                Alert.is_active.is_(True),
            )
            .first()
        )

        if existing_alert is not None:
            results.append(result)
            continue

        event = create_event(
            db=db,
            vehicle_id=state.vehicle_id,
            event_type="communication_loss",
            severity="critical",
            message="Vehicle communication loss detected by background monitor",
            sequence_number=state.sequence_number,
        )

        create_alert(
            db=db,
            vehicle_id=state.vehicle_id,
            alert_type="communication_loss",
            severity="critical",
            message=event.message,
            source_event_id=event.id,
        )

        result["communication_loss_detected"] = True
        result["alert_created"] = True

        results.append(result)

    return results
