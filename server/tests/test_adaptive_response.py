from app.research.adaptive_response import generate_adaptive_response


def test_normal_monitoring():
    result = generate_adaptive_response(
        vehicle_id="TEST-V001",
        sequence_number=10,
        reliability_state="NORMAL",
        contradiction_severity="NONE",
    )
    assert result.response == "NORMAL_MONITORING"
    assert result.research_only is True
    assert result.operational_action == "NO_OPERATIONAL_ACTION"


def test_degraded_increases_observation():
    result = generate_adaptive_response(
        vehicle_id="TEST-V001",
        sequence_number=11,
        reliability_state="DEGRADED",
        contradiction_severity="LOW",
    )
    assert result.response == "INCREASED_OBSERVATION"
    assert result.operational_action == "NO_OPERATIONAL_ACTION"


def test_suspect_requires_revalidation():
    result = generate_adaptive_response(
        vehicle_id="TEST-V001",
        sequence_number=12,
        reliability_state="SUSPECT",
        contradiction_severity="MEDIUM",
    )
    assert result.response == "REQUIRE_REVALIDATION"
    assert result.operational_action == "NO_OPERATIONAL_ACTION"


def test_untrusted_holds_for_recovery():
    result = generate_adaptive_response(
        vehicle_id="TEST-V001",
        sequence_number=13,
        reliability_state="UNTRUSTED",
        contradiction_severity="HIGH",
    )
    assert result.response == "HOLD_FOR_RECOVERY"
    assert result.operational_action == "NO_OPERATIONAL_ACTION"


def test_high_contradiction_overrides_normal_research_response():
    result = generate_adaptive_response(
        vehicle_id="TEST-V001",
        sequence_number=14,
        reliability_state="NORMAL",
        contradiction_severity="HIGH",
    )
    assert result.response == "HOLD_FOR_RECOVERY"
    assert result.operational_action == "NO_OPERATIONAL_ACTION"