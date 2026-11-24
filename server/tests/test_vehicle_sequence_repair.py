
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
from app.database.base import Base
from app.models.vehicle import Vehicle
from app.models.vehicle_history import VehicleHistory
from app.services import vehicle_ingestion as ingestion
from app.services.vehicle_ingestion import (
    VehicleSequenceError,
    ingest_vehicle_state,
)
from app.schemas.vehicles import VehicleStateIn


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    TestSession = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    session = TestSession()

    session.add_all([
        Vehicle(
            display_number=1,
            vehicle_id="TEST-V1",
            device_id="DEVICE-1",
            is_active=True,
        ),
        Vehicle(
            display_number=2,
            vehicle_id="TEST-V2",
            device_id="DEVICE-2",
            is_active=True,
        ),
    ])

    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def safe_ingestion(monkeypatch):
    monkeypatch.setattr(
        ingestion,
        "determine_availability",
        lambda **kwargs: "available",
    )

    monkeypatch.setattr(
        ingestion,
        "is_fresh",
        lambda value: True,
    )

    monkeypatch.setattr(
        ingestion,
        "process_communication_transition",
        lambda **kwargs: None,
    )

    monkeypatch.setattr(
        ingestion,
        "evaluate_route_progress",
        lambda **kwargs: None,
    )

    monkeypatch.setattr(
        ingestion,
        "evaluate_vehicle_evidence",
        lambda **kwargs: SimpleNamespace(
            reliability=0.95,
            contradictions=[],
        ),
    )

    monkeypatch.setattr(
        ingestion,
        "integrate_decision",
        lambda **kwargs: SimpleNamespace(
            reliability_state="reliable",
            contradiction_severity="none",
        ),
    )

    monkeypatch.setattr(
        ingestion,
        "generate_adaptive_response",
        lambda **kwargs: None,
    )

    monkeypatch.setattr(
        ingestion.publisher,
        "publish_from_sync",
        lambda *args, **kwargs: None,
    )


def make_payload(
    vehicle_id="TEST-V1",
    device_id="DEVICE-1",
    boot_id="BOOT-1",
    sequence_number=1,
    latitude=22.5726,
):
    return VehicleStateIn(
        vehicle_id=vehicle_id,
        device_id=device_id,
        boot_id=boot_id,
        sequence_number=sequence_number,
        timestamp=datetime.now(timezone.utc),
        latitude=latitude,
        longitude=88.3639,
        speed=30.0,
        heading=90.0,
        communication_status="connected",
        gps_fix=True,
        satellites=8,
        hdop=1.2,
        gps_source="GPS",
        transport="WIFI",
    )


def history_count(db, vehicle_id):
    return (
        db.query(VehicleHistory)
        .filter(VehicleHistory.vehicle_id == vehicle_id)
        .count()
    )


def test_consecutive_sequences_are_accepted(db, safe_ingestion):
    first = ingest_vehicle_state(
        db,
        make_payload(sequence_number=1),
    )

    # Capture the value before the same ORM object is updated.
    first_sequence = first.sequence_number

    second = ingest_vehicle_state(
        db,
        make_payload(sequence_number=2),
    )

    assert first_sequence == 1
    assert second.sequence_number == 2
    assert history_count(db, "TEST-V1") == 2


def test_identical_retry_does_not_create_duplicate_history(
    db,
    safe_ingestion,
):
    payload = make_payload(sequence_number=1)

    first = ingest_vehicle_state(db, payload)
    first_sequence = first.sequence_number

    second = ingest_vehicle_state(db, payload)

    assert first_sequence == 1
    assert second.sequence_number == 1
    assert history_count(db, "TEST-V1") == 1


def test_same_sequence_with_different_payload_is_rejected(
    db,
    safe_ingestion,
):
    ingest_vehicle_state(
        db,
        make_payload(sequence_number=1),
    )

    conflicting_payload = make_payload(
        sequence_number=1,
        latitude=23.0,
    )

    with pytest.raises(VehicleSequenceError):
        ingest_vehicle_state(db, conflicting_payload)

    assert history_count(db, "TEST-V1") == 1


def test_new_boot_id_starts_new_sequence(
    db,
    safe_ingestion,
):
    ingest_vehicle_state(
        db,
        make_payload(
            boot_id="BOOT-1",
            sequence_number=101,
        ),
    )

    result = ingest_vehicle_state(
        db,
        make_payload(
            boot_id="BOOT-2",
            sequence_number=0,
        ),
    )

    assert result.sequence_number == 0
    assert result.boot_id == "BOOT-2"
    assert history_count(db, "TEST-V1") == 2


def test_old_boot_session_is_not_reactivated(
    db,
    safe_ingestion,
):
    ingest_vehicle_state(
        db,
        make_payload(
            boot_id="BOOT-1",
            sequence_number=1,
        ),
    )

    ingest_vehicle_state(
        db,
        make_payload(
            boot_id="BOOT-2",
            sequence_number=1,
        ),
    )

    with pytest.raises(VehicleSequenceError):
        ingest_vehicle_state(
            db,
            make_payload(
                boot_id="BOOT-1",
                sequence_number=2,
            ),
        )

    assert history_count(db, "TEST-V1") == 2


def test_vehicles_have_independent_sequences(
    db,
    safe_ingestion,
):
    first = ingest_vehicle_state(
        db,
        make_payload(
            vehicle_id="TEST-V1",
            device_id="DEVICE-1",
            boot_id="BOOT-1",
            sequence_number=1,
        ),
    )

    second = ingest_vehicle_state(
        db,
        make_payload(
            vehicle_id="TEST-V2",
            device_id="DEVICE-2",
            boot_id="BOOT-1",
            sequence_number=1,
        ),
    )

    assert first.vehicle_id == "TEST-V1"
    assert second.vehicle_id == "TEST-V2"
    assert history_count(db, "TEST-V1") == 1
    assert history_count(db, "TEST-V2") == 1
