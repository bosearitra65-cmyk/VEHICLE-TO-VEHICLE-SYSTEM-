
from datetime import datetime, timezone
import pytest

from app.research.experiment_engine import (
    ExperimentEngine,
    MechanismType,
    ExperimentStatus,
    RunStatus,
    ValidityStatus,
    FaultTriggerMode,
    FaultStatus,
    BASELINE_V1,
    CANDIDATE_V1,
)


def make_engine():
    e=ExperimentEngine()
    e.create_experiment(
        experiment_id="EXP1",
        name="Communication Failure Study",
        research_question="Can active probing reduce detection latency?",
        objective="Controlled baseline/candidate comparison preparation.",
        created_by="researcher-1",
    )
    e.configure_experiment(
        "EXP1",
        {
            "state_interval_s":5,
            "probe_interval_s":5,
            "timeout_s":15,
            "duration_s":60,
        },
    )
    e.mark_experiment_ready("EXP1")
    return e


def make_run(e, run_id="R1", mechanism=BASELINE_V1, config=None):
    return e.create_run(
        run_id=run_id,
        experiment_id="EXP1",
        run_label=run_id,
        mechanism=mechanism,
        configuration=config,
        snapshot_id=f"S-{run_id}",
        vehicle_ids=["V001"],
        route_id="ROUTE1",
        fault_scenario_id="FAULT1",
        created_by="researcher-1",
    )


def test_experiment_lifecycle():
    e=make_engine()
    exp=e.start_experiment("EXP1")
    assert exp.status is ExperimentStatus.RUNNING
    e.complete_experiment("EXP1")
    assert exp.status is ExperimentStatus.COMPLETED
    assert exp.started_at is not None
    assert exp.completed_at is not None


def test_baseline_candidate_identity_and_version():
    e=make_engine()
    b=make_run(e,"B1",BASELINE_V1)
    c=make_run(e,"C1",CANDIDATE_V1)
    assert b.mechanism.mechanism_type is MechanismType.BASELINE
    assert c.mechanism.mechanism_type is MechanismType.CANDIDATE
    assert b.mechanism.mechanism_version=="BASELINE-v1"
    assert c.mechanism.mechanism_version=="CANDIDATE-v1"


def test_snapshot_is_really_immutable():
    e=make_engine()
    config={
        "timeout_s":15,
        "nested":{"probe_s":5},
        "vehicles":["V001"],
    }
    r=make_run(e,"R2",config=config)
    config["timeout_s"]=99
    config["nested"]["probe_s"]=999
    config["vehicles"].append("V002")
    assert r.configuration_snapshot.values["timeout_s"]==15
    assert r.configuration_snapshot.values["nested"]["probe_s"]==5
    assert tuple(r.configuration_snapshot.values["vehicles"])==("V001",)
    with pytest.raises(TypeError):
        r.configuration_snapshot.values["timeout_s"]=99


def test_run_contains_required_context():
    e=make_engine()
    r=make_run(e,"R3")
    assert r.experiment_id=="EXP1"
    assert r.created_by=="researcher-1"
    assert r.configuration_snapshot.snapshot_id=="S-R3"
    assert r.vehicle_ids==("V001",)
    assert r.route_id=="ROUTE1"
    assert r.fault_scenario_id=="FAULT1"


def test_run_transition_history_and_pause_duration_are_recoverable():
    e=make_engine()
    r=make_run(e,"R4")
    e.start("R4")
    e.pause("R4")
    e.resume("R4")
    e.complete("R4")
    states=[x.state for x in r.transition_history]
    assert states==["PENDING","RUNNING","PAUSED","RUNNING","COMPLETED"]
    assert e.pause_duration_seconds("R4")>=0
    assert r.started_at is not None
    assert r.ended_at is not None


def test_validity_requires_observation():
    e=make_engine()
    r=make_run(e,"R5")
    e.start("R5")
    e.complete("R5")
    assert r.validity_status is ValidityStatus.INCOMPLETE
    assert r.validity_checks["required_vehicles"] is True
    assert r.validity_checks["configuration_recorded"] is True
    assert r.validity_checks["observations_available"] is False


def test_validity_becomes_valid_when_required_context_exists():
    e=make_engine()
    r=make_run(e,"R6")
    e.start("R6")
    e.record_observation("R6",{"sequence":1,"source":"vehicle"})
    e.complete("R6")
    assert r.validity_status is ValidityStatus.VALID
    assert all(r.validity_checks.values())


def test_abort_is_invalid():
    e=make_engine()
    r=make_run(e,"R7")
    e.start("R7")
    e.abort("R7",reason="CONTROLLED_COMMUNICATION_LOSS")
    assert r.status is RunStatus.ABORTED
    assert r.validity_status is ValidityStatus.INVALID
    assert r.abort_reason=="CONTROLLED_COMMUNICATION_LOSS"


def test_fault_modes_and_lifecycle():
    e=make_engine()
    for mode in (
        FaultTriggerMode.CONTROLLED,
        FaultTriggerMode.EXTERNAL,
        FaultTriggerMode.MANUAL,
    ):
        fault=e.create_fault_scenario(
            fault_scenario_id=f"F-{mode.value}",
            name="Communication Loss",
            fault_type="COMMUNICATION_LOSS",
            target_vehicle_id="V001",
            trigger_mode=mode,
            created_by="researcher-1",
            planned_start_at=datetime.now(timezone.utc),
            planned_duration_seconds=30,
            configuration={"duration_s":30},
        )
        assert fault.status is FaultStatus.SCHEDULED
        e.activate_fault(fault.fault_scenario_id)
        assert fault.status is FaultStatus.ACTIVE
        e.end_fault(fault.fault_scenario_id)
        assert fault.status is FaultStatus.ENDED
        assert fault.actual_start_at is not None
        assert fault.actual_end_at is not None


def test_research_only_boundary():
    assert ExperimentEngine.RESEARCH_ONLY is True
    assert ExperimentEngine.OPERATIONAL_ACTION=="NO_OPERATIONAL_ACTION"
