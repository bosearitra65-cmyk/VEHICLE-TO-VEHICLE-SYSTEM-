from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
import app.api.routes.research as research_routes
from app.api.dependencies import get_current_user, get_db
from app.auth.permissions import Permission
from app.auth.roles import UserRole
from app.database.base import Base
from app.models.route import Route
from app.models.vehicle import Vehicle
from main import app


@pytest.fixture
def api():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    state = {"role": UserRole.ADMINISTRATOR.value}

    def override_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    def override_user():
        return SimpleNamespace(id=1, role=state["role"], is_active=True)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user

    with TestSession() as db:
        db.add(Vehicle(display_number=1, vehicle_id="TEST-V1", is_active=True))
        db.add(Route(route_id="TEST-R1", origin="A", destination="B", geometry="{}"))
        db.commit()

    client = TestClient(app)
    try:
        yield client, state
    finally:
        client.close()
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        Base.metadata.drop_all(engine)
        engine.dispose()


def ready_experiment(client):
    result = client.post("/api/v1/research/experiments", json={
        "experiment_id": "TEST-EXP",
        "name": "API integration test",
        "research_question": "Does the run lifecycle work?",
        "objective": "Verify persistence and validity checks",
    })
    assert result.status_code == 201, result.text

    result = client.put(
        "/api/v1/research/experiments/TEST-EXP/configuration",
        json={"values": {"sample_rate": 1}, "configuration_version": "test-v1"},
    )
    assert result.status_code == 200, result.text

    result = client.post("/api/v1/research/experiments/TEST-EXP/ready")
    assert result.status_code == 200, result.text


def create_run(client, **overrides):
    payload = {
        "run_label": "baseline-test",
        "mechanism_type": "BASELINE",
        "mechanism_version": "test-v1",
        "vehicle_ids": ["TEST-V1"],
        "route_id": "TEST-R1",
    }
    payload.update(overrides)
    return client.post("/api/v1/research/experiments/TEST-EXP/runs", json=payload)


def test_experiment_run_lifecycle_and_valid_completion(api):
    client, _ = api
    ready_experiment(client)

    result = create_run(client)
    assert result.status_code == 201, result.text
    run_id = result.json()["data"]["run_id"]

    result = client.post(f"/api/v1/research/runs/{run_id}/start")
    assert result.status_code == 200, result.text

    result = client.post(
        f"/api/v1/research/runs/{run_id}/observations",
        json={"observation": {"sample": 1}},
    )
    assert result.status_code == 200, result.text

    result = client.post(f"/api/v1/research/runs/{run_id}/complete")
    assert result.status_code == 200, result.text
    assert result.json()["data"]["status"] == "COMPLETED"
    assert result.json()["data"]["validity_status"] == "VALID"


def test_unknown_vehicle_is_rejected(api):
    client, _ = api
    ready_experiment(client)
    result = create_run(client, vehicle_ids=["DOES-NOT-EXIST"])
    assert result.status_code == 422, result.text
    assert result.json()["detail"]["code"] == "UNKNOWN_VEHICLE_IDS"


def test_unknown_route_is_rejected(api):
    client, _ = api
    ready_experiment(client)
    result = create_run(client, route_id="DOES-NOT-EXIST")
    assert result.status_code == 422, result.text
    assert result.json()["detail"] == "UNKNOWN_ROUTE_ID"


def test_fault_scenario_requires_fault_control_permission(api, monkeypatch):
    client, _ = api
    ready_experiment(client)
    original = research_routes.has_permission

    def deny_fault_control(user, permission):
        if permission == Permission.RESEARCH_FAULT_CONTROL:
            return False
        return original(user, permission)

    monkeypatch.setattr(research_routes, "has_permission", deny_fault_control)
    result = create_run(client, fault_scenario_id="TEST-FAULT")
    assert result.status_code == 403, result.text
    assert result.json()["detail"] == "FAULT_CONTROL_PERMISSION_REQUIRED"
