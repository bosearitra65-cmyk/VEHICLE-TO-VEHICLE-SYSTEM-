from datetime import datetime, timezone
from sqlalchemy import func

from app.database.session import SessionLocal
from app.models.event import Event
from app.models.vehicle import Vehicle
from app.models.vehicle_history import VehicleHistory
from app.models.vehicle_session import VehicleSession
from app.models.vehicle_state import VehicleState
from app.schemas.vehicles import VehicleStateIn
from app.services.vehicle_ingestion import ingest_vehicle_state


def test_vehicle_ingestion_commits_state_history_and_session():
    db = SessionLocal()

    vehicle_id = "TEST-INGEST-V001"
    device_id = "TEST-INGEST-D001"
    boot_id = "TEST-INGEST-BOOT001"

    try:
        next_display_number = (db.query(func.max(Vehicle.display_number)).scalar() or 0) + 1
        vehicle = Vehicle(
            display_number=next_display_number,
            vehicle_id=vehicle_id,
            device_id=device_id,
            name="Ingestion Test Vehicle",
            is_active=True,
        )
        db.add(vehicle)
        db.commit()

        payload = VehicleStateIn(
            vehicle_id=vehicle_id,
            sequence_number=1,
            timestamp=datetime.now(timezone.utc),
            latitude=22.5726,
            longitude=88.3639,
            speed=25.0,
            heading=90.0,
            communication_status="live",
            device_id=device_id,
            boot_id=boot_id,
            gps_fix=True,
            satellites=10,
            hdop=1.2,
            gps_source="test",
            transport="wifi",
            convoy_id=None,
            role="test",
        )

        state = ingest_vehicle_state(
            db=db,
            payload=payload,
        )

        assert state.vehicle_id == vehicle_id
        assert state.sequence_number == 1

        history = (
            db.query(VehicleHistory)
            .filter(VehicleHistory.vehicle_id == vehicle_id)
            .all()
        )

        sessions = (
            db.query(VehicleSession)
            .filter(VehicleSession.vehicle_id == vehicle_id)
            .all()
        )

        events = (
            db.query(Event)
            .filter(Event.vehicle_id == vehicle_id)
            .all()
        )

        stored_state = (
            db.query(VehicleState)
            .filter(VehicleState.vehicle_id == vehicle_id)
            .first()
        )

        assert stored_state is not None
        assert stored_state.sequence_number == 1
        assert len(history) == 1
        assert history[0].sequence_number == 1
        assert len(sessions) == 1
        assert sessions[0].boot_id == boot_id
        assert events == []

    finally:
        db.rollback()
        db.query(VehicleHistory).filter(
            VehicleHistory.vehicle_id == vehicle_id
        ).delete(synchronize_session=False)

        db.query(VehicleSession).filter(
            VehicleSession.vehicle_id == vehicle_id
        ).delete(synchronize_session=False)

        db.query(Event).filter(
            Event.vehicle_id == vehicle_id
        ).delete(synchronize_session=False)

        db.query(VehicleState).filter(
            VehicleState.vehicle_id == vehicle_id
        ).delete(synchronize_session=False)

        db.query(Vehicle).filter(
            Vehicle.vehicle_id == vehicle_id
        ).delete(synchronize_session=False)

        db.commit()
        db.close()
