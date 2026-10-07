from datetime import datetime, timedelta

from types import SimpleNamespace

from app.research.vehicle_evidence_adapter import (
    evaluate_vehicle_evidence,
)


def make_state():
    return SimpleNamespace(
        vehicle_id="TEST-V001",
        sequence_number=10,
        timestamp=datetime.utcnow(),
        latitude=22.5726,
        longitude=88.3639,
        speed=10.0,
        heading=90.0,
        communication_status="CONNECTED",
        convoy_id="CONVOY-TEST",
        role="FOLLOWER",
    )


def test_all_six_evidence_dimensions_and_read_only():
    state = make_state()
    previous_time = state.timestamp - timedelta(seconds=5)

    route = SimpleNamespace(
        deviation_status="NORMAL",
        distance_from_route_m=10.0,
    )

    result = evaluate_vehicle_evidence(
        current_state=state,
        previous_timestamp=previous_time,
        previous_latitude=state.latitude,
        previous_longitude=state.longitude,
        previous_speed=10.0,
        availability="AVAILABLE",
        route_result=route,
    )

    assert set(result.evidence) == {
        "temporal",
        "spatial",
        "motion",
        "route",
        "communication",
        "convoy",
    }

    assert all(
        0.0 <= value <= 1.0
        for value in result.evidence.values()
    )

    assert result.reliability.state in {
        "NORMAL",
        "DEGRADED",
        "SUSPECT",
        "UNTRUSTED",
    }

    assert result.read_only is True


def test_route_deviation_reduces_route_evidence():
    state = make_state()

    route = SimpleNamespace(
        deviation_status="DEVIATED",
        distance_from_route_m=250.0,
    )

    result = evaluate_vehicle_evidence(
        current_state=state,
        availability="AVAILABLE",
        route_result=route,
    )

    assert result.evidence["route"] == 0.0
    assert any(
        item.contradiction_type == "ROUTE"
        for item in result.contradictions
    )


def test_disconnected_reduces_communication_evidence():
    state = make_state()
    state.communication_status = "DISCONNECTED"

    result = evaluate_vehicle_evidence(
        current_state=state,
        availability="UNAVAILABLE",
    )

    assert result.evidence["communication"] == 0.0
