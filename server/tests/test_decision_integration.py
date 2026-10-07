from types import SimpleNamespace

from app.research.decision_integration import integrate_decision


def r(score, state):
    return SimpleNamespace(score=score, state=state)


def c(severity):
    return SimpleNamespace(severity=severity)


def test_reliability_only():
    result = integrate_decision(
        vehicle_id="TEST-V001",
        sequence_number=10,
        reliability=r(0.92, "NORMAL"),
        contradictions=(),
    )
    assert result.reliability_score == 0.92
    assert result.reliability_state == "NORMAL"
    assert result.contradiction_severity == "NONE"
    assert result.contradiction_count == 0
    assert result.decision_basis == "RELIABILITY_ONLY"
    assert result.operational_action == "NO_OPERATIONAL_ACTION"
    assert result.read_only is True


def test_highest_contradiction():
    result = integrate_decision(
        vehicle_id="TEST-V001",
        sequence_number=11,
        reliability=r(0.55, "DEGRADED"),
        contradictions=(c("LOW"), c("HIGH"), c("MEDIUM")),
    )
    assert result.reliability_state == "DEGRADED"
    assert result.contradiction_severity == "HIGH"
    assert result.contradiction_count == 3
    assert result.decision_basis == "RELIABILITY_PLUS_CONTRADICTION"
    assert result.operational_action == "NO_OPERATIONAL_ACTION"


def test_untrusted_remains_non_operational():
    result = integrate_decision(
        vehicle_id="TEST-V001",
        sequence_number=12,
        reliability=r(0.20, "UNTRUSTED"),
        contradictions=(c("HIGH"),),
    )
    assert result.reliability_state == "UNTRUSTED"
    assert result.contradiction_severity == "HIGH"
    assert result.operational_action == "NO_OPERATIONAL_ACTION"
    assert result.read_only is True