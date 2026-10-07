from sqlalchemy.orm import Session

from app.config.constants import EVENT_GPS_QUALITY, EVENT_SEQUENCE_GAP
from app.database.repositories.vehicle_state_repository import VehicleStateRepository
from app.models.vehicle_state import VehicleState
from app.schemas.vehicles import VehicleStateIn
from app.services.alert_resolution import resolve_communication_alerts
from app.services.availability import determine_availability
from app.services.communication_events import process_communication_transition
from app.services.event_alert_service import process_event_for_alert
from app.services.event_service import create_event
from app.services.freshness import is_fresh
from app.services.gps_quality import (
    VehicleGPSQualityError,
    validate_gps_quality,
)
from app.services.sequence_validation import SequenceStatus, validate_sequence
from app.services.timestamp_validation import validate_vehicle_timestamp
from app.services.vehicle_identity import validate_vehicle_identity
from app.services.vehicle_history_service import create_vehicle_history
from app.services.session_service import get_or_create_vehicle_session
from app.services.route_progress.service import evaluate_route_progress
from app.realtime.publisher import publisher
from app.research.vehicle_evidence_adapter import evaluate_vehicle_evidence
from app.research.decision_integration import integrate_decision
from app.research.adaptive_response import generate_adaptive_response


class VehicleSequenceError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def ingest_vehicle_state(
    db: Session,
    payload: VehicleStateIn,
) -> VehicleState:
    validate_vehicle_identity(
        db=db,
        vehicle_id=payload.vehicle_id,
        device_id=payload.device_id,
    )

    validate_vehicle_timestamp(payload.timestamp)

    try:
        validate_gps_quality(payload)
    except VehicleGPSQualityError as exc:
        event = create_event(
            db=db,
            vehicle_id=payload.vehicle_id,
            event_type=EVENT_GPS_QUALITY,
            severity="warning",
            message=str(exc),
            sequence_number=payload.sequence_number,
        )
        process_event_for_alert(db=db, event=event)

        db.commit()

        raise

    state_repository = VehicleStateRepository(db)

    state = state_repository.get_by_vehicle_id(
        payload.vehicle_id,
    )

    previous_availability = None

    if state is not None:
        previous_fresh = is_fresh(state.timestamp)

        previous_availability = determine_availability(
            is_fresh=previous_fresh,
            communication_status=state.communication_status,
        )

    previous_latitude = state.latitude if state else None
    previous_longitude = state.longitude if state else None
    previous_timestamp = state.timestamp if state else None
    previous_speed = state.speed if state else None
    previous_heading = state.heading if state else None

    last_sequence = state.sequence_number if state else None

    sequence_result = validate_sequence(
        incoming_sequence=payload.sequence_number,
        last_sequence=last_sequence,
    )

    if sequence_result.status == SequenceStatus.DUPLICATE:
        raise VehicleSequenceError(
            "Duplicate vehicle state sequence"
        )

    if sequence_result.status == SequenceStatus.OUT_OF_ORDER:
        raise VehicleSequenceError(
            "Vehicle state sequence is out of order"
        )

    if sequence_result.status == SequenceStatus.GAP:
        create_event(
            db=db,
            vehicle_id=payload.vehicle_id,
            event_type=EVENT_SEQUENCE_GAP,
            severity="warning",
            message=(
                f"Sequence gap detected: "
                f"{sequence_result.gap_start}-"
                f"{sequence_result.gap_end}"
            ),
            sequence_number=payload.sequence_number,
        )

    if payload.boot_id is not None:
        get_or_create_vehicle_session(
            db=db,
            vehicle_id=payload.vehicle_id,
            boot_id=payload.boot_id,
        )

    current_fresh = is_fresh(payload.timestamp)

    current_availability = determine_availability(
        is_fresh=current_fresh,
        communication_status=payload.communication_status,
    )

    communication_event = process_communication_transition(
        db=db,
        vehicle_id=payload.vehicle_id,
        previous_availability=previous_availability,
        current_availability=current_availability,
        sequence_number=payload.sequence_number,
    )

    if communication_event is not None:
        if communication_event.event_type == "communication_loss":
            process_event_for_alert(
                db=db,
                event=communication_event,
            )

        elif communication_event.event_type == "communication_recovery":
            resolve_communication_alerts(
                db=db,
                vehicle_id=payload.vehicle_id,
            )

    if state is None:
        state = state_repository.create(
            vehicle_id=payload.vehicle_id,
            sequence_number=payload.sequence_number,
            timestamp=payload.timestamp,
            latitude=payload.latitude,
            longitude=payload.longitude,
            speed=payload.speed,
            heading=payload.heading,
            communication_status=payload.communication_status,
            device_id=payload.device_id,
            boot_id=payload.boot_id,
            gps_fix=payload.gps_fix,
            satellites=payload.satellites,
            hdop=payload.hdop,
            gps_source=payload.gps_source,
            transport=payload.transport,
            convoy_id=payload.convoy_id,
            role=payload.role,
        )
    else:
        state.sequence_number = payload.sequence_number
        state.timestamp = payload.timestamp
        state.latitude = payload.latitude
        state.longitude = payload.longitude
        state.speed = payload.speed
        state.heading = payload.heading
        state.communication_status = payload.communication_status
        state.device_id = payload.device_id
        state.boot_id = payload.boot_id
        state.gps_fix = payload.gps_fix
        state.satellites = payload.satellites
        state.hdop = payload.hdop
        state.gps_source = payload.gps_source
        state.transport = payload.transport
        state.convoy_id = payload.convoy_id
        state.role = payload.role

    create_vehicle_history(
        db=db,
        state=state,
    )

    route_progress_result = evaluate_route_progress(
        db=db,
        current_state=state,
        previous_latitude=previous_latitude,
        previous_longitude=previous_longitude,
    )

    # Step 10.5.3 research consumer: read-only evidence extraction.
    # This result is intentionally transient; persistence/decision logic
    # belongs to later Stage 10 steps.
    research_evidence = evaluate_vehicle_evidence(
        current_state=state,
        previous_timestamp=previous_timestamp,
        previous_latitude=previous_latitude,
        previous_longitude=previous_longitude,
        previous_speed=previous_speed,
        availability=current_availability,
        route_result=route_progress_result,
    )

    # Keep the value available for the current ingestion execution only.
    # No authoritative DB/realtime mutation is performed by the adapter.
    _ = research_evidence

    research_decision = integrate_decision(
        vehicle_id=state.vehicle_id,
        sequence_number=state.sequence_number,
        reliability=research_evidence.reliability,
        contradictions=research_evidence.contradictions,
    )

    _ = research_decision

    adaptive_response = generate_adaptive_response(
        vehicle_id=state.vehicle_id,
        sequence_number=state.sequence_number,
        reliability_state=research_decision.reliability_state,
        contradiction_severity=research_decision.contradiction_severity,
    )

    _ = adaptive_response

    db.commit()
    db.refresh(state)

    publisher.publish_from_sync(
        "VEHICLE_STATE_UPDATED",
        "vehicle",
        state.vehicle_id,
        {
            "vehicle_id": state.vehicle_id,
            "sequence_number": state.sequence_number,
            "timestamp": state.timestamp.isoformat(),
            "latitude": state.latitude,
            "longitude": state.longitude,
            "speed": state.speed,
            "heading": state.heading,
            "communication_status": state.communication_status,
            "device_id": state.device_id,
            "boot_id": state.boot_id,
            "gps_fix": state.gps_fix,
            "satellites": state.satellites,
            "hdop": state.hdop,
            "gps_source": state.gps_source,
            "transport": state.transport,
            "convoy_id": state.convoy_id,
            "role": state.role,
        },
        version=state.sequence_number,
        vehicle_id=state.vehicle_id,
        convoy_id=state.convoy_id,
    )

    return state
