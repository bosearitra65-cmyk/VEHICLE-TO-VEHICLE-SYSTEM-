
import hashlib
import json

from sqlalchemy.orm import Session

from app.config.constants import EVENT_GPS_QUALITY, EVENT_SEQUENCE_GAP
from app.database.repositories.vehicle_state_repository import VehicleStateRepository
from app.database.repositories.vehicle_repository import VehicleRepository
from app.database.repositories.vehicle_session_repository import (
    VehicleSessionRepository,
)
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


def _calculate_payload_hash(payload: VehicleStateIn) -> str:
    payload_data = payload.model_dump(mode="json")

    canonical_payload = json.dumps(
        payload_data,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        canonical_payload.encode("utf-8")
    ).hexdigest()


def ingest_vehicle_state(
    db: Session,
    payload: VehicleStateIn,
) -> VehicleState:
    # PostgreSQL: serialize telemetry updates for this vehicle.
    # SQLite does not enforce SELECT FOR UPDATE.
    vehicle_repository = VehicleRepository(db)

    vehicle_repository.get_by_vehicle_id_for_update(
        payload.vehicle_id,
    )

    validate_vehicle_identity(
        db=db,
        vehicle_id=payload.vehicle_id,
        device_id=payload.device_id,
    )

    validate_vehicle_timestamp(payload.timestamp)

    payload_hash = _calculate_payload_hash(payload)

    state_repository = VehicleStateRepository(db)
    history_repository = VehicleSessionRepository(db)

    # Check whether this exact packet has already been recorded.
    # This also allows safe retries from previously inactive boot sessions.
    if payload.boot_id is not None:
        from app.database.repositories.vehicle_history_repository import (
            VehicleHistoryRepository,
        )

        history_repository_for_packets = VehicleHistoryRepository(db)

        existing_history = (
            history_repository_for_packets.get_by_session_sequence(
                vehicle_id=payload.vehicle_id,
                device_id=payload.device_id,
                boot_id=payload.boot_id,
                sequence_number=payload.sequence_number,
            )
        )

        if existing_history is not None:
            if existing_history.payload_hash == payload_hash:
                existing_state = state_repository.get_by_vehicle_id(
                    payload.vehicle_id,
                )

                if existing_state is None:
                    raise VehicleSequenceError(
                        "Previously recorded packet has no current vehicle state."
                    )

                return existing_state

            raise VehicleSequenceError(
                "Sequence conflict: this boot session already used "
                "this sequence number with different telemetry data."
            )

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

    state = state_repository.get_by_vehicle_id(
        payload.vehicle_id,
    )

    previous_availability = None

    if state is not None:
        previous_fresh = is_fresh(state.updated_at)

        previous_availability = determine_availability(
            is_fresh=previous_fresh,
            communication_status=state.communication_status,
        )

    previous_latitude = state.latitude if state else None
    previous_longitude = state.longitude if state else None
    previous_timestamp = state.timestamp if state else None
    previous_speed = state.speed if state else None
    previous_heading = state.heading if state else None

    vehicle_session = None

    if payload.boot_id is not None:
        try:
            vehicle_session = get_or_create_vehicle_session(
                db=db,
                vehicle_id=payload.vehicle_id,
                boot_id=payload.boot_id,
            )
        except ValueError as exc:
            raise VehicleSequenceError(str(exc)) from exc

        last_sequence = vehicle_session.last_sequence_number

    else:
        # Legacy devices without a boot ID retain vehicle-wide validation.
        last_sequence = state.sequence_number if state else None

    sequence_result = validate_sequence(
        incoming_sequence=payload.sequence_number,
        last_sequence=last_sequence,
    )

    if sequence_result.status == SequenceStatus.DUPLICATE:
        raise VehicleSequenceError(
            "Duplicate sequence number without a matching recorded packet."
        )

    if sequence_result.status == SequenceStatus.OUT_OF_ORDER:
        raise VehicleSequenceError(
            f"Out-of-order sequence number. "
            f"Expected {sequence_result.expected_sequence}, "
            f"received {payload.sequence_number}."
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

    current_availability = determine_availability(
        is_fresh=True,
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
        payload_hash=payload_hash,
    )

    # Advance the session counter only for a newly accepted packet.
    if vehicle_session is not None:
        VehicleSessionRepository(db).update_sequence(
            session=vehicle_session,
            sequence_number=payload.sequence_number,
            payload_hash=payload_hash,
        )

    route_progress_result = evaluate_route_progress(
        db=db,
        current_state=state,
        previous_latitude=previous_latitude,
        previous_longitude=previous_longitude,
    )

    research_evidence = evaluate_vehicle_evidence(
        current_state=state,
        previous_timestamp=previous_timestamp,
        previous_latitude=previous_latitude,
        previous_longitude=previous_longitude,
        previous_speed=previous_speed,
        availability=current_availability,
        route_result=route_progress_result,
    )

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
