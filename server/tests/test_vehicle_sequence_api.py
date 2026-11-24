
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
import app.services.vehicle_ingestion as ingestion

from app.api.dependencies import get_db, require_device_auth
from app.database.base import Base
from app.models.vehicle import Vehicle
from main import app


@pytest.fixture
def api_setup(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    vehicle = Vehicle(
        display_number="TEST-API-1",
        vehicle_id="TEST-API-1",
        device_id="DEVICE-API-1",
        device_auth_enabled=False,
    )

    db.add(vehicle)
    db.commit()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    monkeypatch.setattr(
        ingestion,
        "determine_availability",
        lambda *args, **kwargs: "available",
    )
    monkeypatch.setattr(
        ingestion,
        "is_fresh",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        ingestion,
        "process_communication_transition",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        ingestion,
        "evaluate_route_progress",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        ingestion,
        "evaluate_vehicle_evidence",
        lambda *args, **kwargs: type(
            "Evidence",
            (),
            {"reliability": 0.95, "contradictions": []},
        )(),
    )
    monkeypatch.setattr(
        ingestion,
        "integrate_decision",
        lambda *args, **kwargs: type(
            "Decision",
            (),
            {
                "reliability_state": "reliable",
                "contradiction_severity": "none",
            },
        )(),
    )
    monkeypatch.setattr(
        ingestion,
        "generate_adaptive_response",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        ingestion.publisher,
        "publish_from_sync",
        lambda *args, **kwargs: None,
    )

    client = TestClient(app)

    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(require_device_auth, None)
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def make_api_payload():
    return {
        "vehicle_id": "TEST-API-1",
        "device_id": "DEVICE-API-1",
        "boot_id": "BOOT-API-1",
        "sequence_number": 1,
        "latitude": 22.5726,
        "longitude": 88.3639,
        "speed": 30,
        "heading": 90,
        "communication_status": "connected",
        "gps_fix": True,
        "satellites": 8,
        "hdop": 1.2,
        "gps_source": "GPS",
        "transport": "WIFI",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def test_first_packet_and_identical_retry_return_success(api_setup):
    app.dependency_overrides[require_device_auth] = lambda: None

    payload = make_api_payload()

    first = api_setup.post(
        "/api/v1/vehicle/state",
        json=payload,
    )
    retry = api_setup.post(
        "/api/v1/vehicle/state",
        json=payload,
    )

    assert first.status_code == 200, first.text
    assert retry.status_code == 200, retry.text


def test_conflicting_duplicate_sequence_returns_409(api_setup):
    app.dependency_overrides[require_device_auth] = lambda: None

    payload = make_api_payload()

    first = api_setup.post(
        "/api/v1/vehicle/state",
        json=payload,
    )
    assert first.status_code == 200, first.text

    conflicting_payload = payload.copy()
    conflicting_payload["latitude"] = 23.0000

    second = api_setup.post(
        "/api/v1/vehicle/state",
        json=conflicting_payload,
    )

    assert second.status_code == 409, second.text


def test_incomplete_device_authentication_is_rejected(api_setup):
    payload = make_api_payload()

    response = api_setup.post(
        "/api/v1/vehicle/state",
        json=payload,
        headers={"X-Device-ID": "DEVICE-API-1"},
    )

    assert response.status_code == 401, response.text
