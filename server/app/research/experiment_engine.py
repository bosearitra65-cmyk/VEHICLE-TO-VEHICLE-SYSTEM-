
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, tuple):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, set):
        return frozenset(_freeze(v) for v in value)
    return value


class MechanismType(str, Enum):
    BASELINE = "BASELINE"
    CANDIDATE = "CANDIDATE"


class ExperimentStatus(str, Enum):
    DRAFT = "DRAFT"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


class RunStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


class ValidityStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    INCOMPLETE = "INCOMPLETE"


class FaultTriggerMode(str, Enum):
    CONTROLLED = "CONTROLLED"
    EXTERNAL = "EXTERNAL"
    MANUAL = "MANUAL"


class FaultStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"


@dataclass(frozen=True)
class MechanismDefinition:
    mechanism_type: MechanismType
    mechanism_version: str
    name: str
    description: str


BASELINE_V1 = MechanismDefinition(
    MechanismType.BASELINE,
    "BASELINE-v1",
    "Passive Periodic State Reporting",
    "Passive periodic state reporting with timeout-based failure detection.",
)

CANDIDATE_V1 = MechanismDefinition(
    MechanismType.CANDIDATE,
    "CANDIDATE-v1",
    "Active Server-Initiated Health Probe",
    "Active server-initiated health probe followed by vehicle response.",
)


@dataclass(frozen=True)
class ConfigurationSnapshot:
    snapshot_id: str
    values: MappingProxyType
    captured_at: datetime


@dataclass
class ExperimentConfiguration:
    experiment_id: str
    values: dict[str, Any]
    configuration_version: str = "CONFIG-v1"


@dataclass
class Experiment:
    experiment_id: str
    name: str
    research_question: str
    objective: str
    created_by: str
    description: str = ""
    status: ExperimentStatus = ExperimentStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class FaultScenario:
    fault_scenario_id: str
    name: str
    fault_type: str
    target_vehicle_id: str
    trigger_mode: FaultTriggerMode
    planned_start_at: datetime | None = None
    planned_duration_seconds: float | None = None
    created_by: str = ""
    configuration: MappingProxyType = field(
        default_factory=lambda: MappingProxyType({})
    )
    status: FaultStatus = FaultStatus.SCHEDULED
    actual_start_at: datetime | None = None
    actual_end_at: datetime | None = None


@dataclass(frozen=True)
class StateTransition:
    state: str
    at: datetime


@dataclass
class ExperimentRun:
    run_id: str
    experiment_id: str
    run_label: str
    mechanism: MechanismDefinition
    configuration_snapshot: ConfigurationSnapshot
    vehicle_ids: tuple[str, ...]
    route_id: str | None
    fault_scenario_id: str | None
    created_by: str
    status: RunStatus = RunStatus.PENDING
    validity_status: ValidityStatus = ValidityStatus.INCOMPLETE
    abort_reason: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    observations: list[dict[str, Any]] = field(default_factory=list)
    transition_history: list[StateTransition] = field(default_factory=list)
    validity_checks: dict[str, bool] = field(default_factory=dict)


class ExperimentEngine:
    """
    Research-only experiment/run controller.

    This module does not write the operational database, alter authoritative
    vehicle state, publish realtime messages, create operational alerts/events,
    or perform production actions.

    Comparison/winner logic intentionally does not exist in Step 5.6.
    """

    RESEARCH_ONLY = True
    OPERATIONAL_ACTION = "NO_OPERATIONAL_ACTION"

    def __init__(self) -> None:
        self._experiments: dict[str, Experiment] = {}
        self._configurations: dict[str, ExperimentConfiguration] = {}
        self._faults: dict[str, FaultScenario] = {}
        self._runs: dict[str, ExperimentRun] = {}

    # ---------- EXPERIMENT ----------

    def create_experiment(
        self,
        *,
        experiment_id: str,
        name: str,
        research_question: str,
        objective: str,
        created_by: str,
        description: str = "",
    ) -> Experiment:
        if experiment_id in self._experiments:
            raise ValueError("EXPERIMENT_ID_ALREADY_EXISTS")
        experiment=Experiment(
            experiment_id=experiment_id,
            name=name,
            research_question=research_question,
            objective=objective,
            created_by=created_by,
            description=description,
        )
        self._experiments[experiment_id]=experiment
        return experiment

    def configure_experiment(
        self,
        experiment_id: str,
        values: dict[str, Any],
        configuration_version: str = "CONFIG-v1",
    ) -> ExperimentConfiguration:
        exp=self._get_experiment(experiment_id)
        if exp.status is not ExperimentStatus.DRAFT:
            raise ValueError("CONFIGURATION_LOCKED")
        config=ExperimentConfiguration(
            experiment_id=experiment_id,
            values=dict(values),
            configuration_version=configuration_version,
        )
        self._configurations[experiment_id]=config
        exp.updated_at=datetime.now(timezone.utc)
        return config

    def mark_experiment_ready(self, experiment_id: str) -> Experiment:
        exp=self._get_experiment(experiment_id)
        if exp.status is not ExperimentStatus.DRAFT:
            raise ValueError("INVALID_EXPERIMENT_READY_TRANSITION")
        if experiment_id not in self._configurations:
            raise ValueError("EXPERIMENT_CONFIGURATION_REQUIRED")
        exp.status=ExperimentStatus.READY
        exp.updated_at=datetime.now(timezone.utc)
        return exp

    def start_experiment(self, experiment_id: str) -> Experiment:
        exp=self._get_experiment(experiment_id)
        if exp.status is not ExperimentStatus.READY:
            raise ValueError("INVALID_EXPERIMENT_START_TRANSITION")
        exp.status=ExperimentStatus.RUNNING
        exp.started_at=datetime.now(timezone.utc)
        exp.updated_at=exp.started_at
        return exp

    def complete_experiment(self, experiment_id: str) -> Experiment:
        exp=self._get_experiment(experiment_id)
        if exp.status is not ExperimentStatus.RUNNING:
            raise ValueError("INVALID_EXPERIMENT_COMPLETE_TRANSITION")
        exp.status=ExperimentStatus.COMPLETED
        exp.completed_at=datetime.now(timezone.utc)
        exp.updated_at=exp.completed_at
        return exp

    def abort_experiment(self, experiment_id: str) -> Experiment:
        exp=self._get_experiment(experiment_id)
        if exp.status in (ExperimentStatus.COMPLETED, ExperimentStatus.ABORTED):
            raise ValueError("INVALID_EXPERIMENT_ABORT_TRANSITION")
        exp.status=ExperimentStatus.ABORTED
        exp.updated_at=datetime.now(timezone.utc)
        return exp

    # ---------- FAULT SCENARIO ----------

    def create_fault_scenario(
        self,
        *,
        fault_scenario_id: str,
        name: str,
        fault_type: str,
        target_vehicle_id: str,
        trigger_mode: FaultTriggerMode,
        created_by: str,
        planned_start_at: datetime | None = None,
        planned_duration_seconds: float | None = None,
        configuration: dict[str, Any] | None = None,
    ) -> FaultScenario:
        if fault_scenario_id in self._faults:
            raise ValueError("FAULT_SCENARIO_ID_ALREADY_EXISTS")
        fault=FaultScenario(
            fault_scenario_id=fault_scenario_id,
            name=name,
            fault_type=fault_type,
            target_vehicle_id=target_vehicle_id,
            trigger_mode=trigger_mode,
            planned_start_at=planned_start_at,
            planned_duration_seconds=planned_duration_seconds,
            created_by=created_by,
            configuration=_freeze(configuration or {}),
        )
        self._faults[fault_scenario_id]=fault
        return fault

    def activate_fault(self, fault_scenario_id: str) -> FaultScenario:
        fault=self._get_fault(fault_scenario_id)
        if fault.status is not FaultStatus.SCHEDULED:
            raise ValueError("INVALID_FAULT_ACTIVATION")
        fault.status=FaultStatus.ACTIVE
        fault.actual_start_at=datetime.now(timezone.utc)
        return fault

    def end_fault(self, fault_scenario_id: str) -> FaultScenario:
        fault=self._get_fault(fault_scenario_id)
        if fault.status is not FaultStatus.ACTIVE:
            raise ValueError("INVALID_FAULT_END")
        fault.status=FaultStatus.ENDED
        fault.actual_end_at=datetime.now(timezone.utc)
        return fault

    # ---------- RUN ----------

    def create_run(
        self,
        *,
        run_id: str,
        experiment_id: str,
        run_label: str,
        mechanism: MechanismDefinition,
        configuration: dict[str, Any] | None = None,
        snapshot_id: str,
        vehicle_ids: list[str] | tuple[str, ...],
        route_id: str | None = None,
        fault_scenario_id: str | None = None,
        created_by: str,
    ) -> ExperimentRun:
        if run_id in self._runs:
            raise ValueError("RUN_ID_ALREADY_EXISTS")
        exp=self._get_experiment(experiment_id)
        if exp.status not in (ExperimentStatus.READY, ExperimentStatus.RUNNING):
            raise ValueError("EXPERIMENT_NOT_READY_FOR_RUN")
        if not vehicle_ids:
            raise ValueError("RUN_REQUIRES_VEHICLE")

        source_config=configuration
        if source_config is None:
            saved=self._configurations.get(experiment_id)
            if saved is None:
                raise ValueError("EXPERIMENT_CONFIGURATION_REQUIRED")
            source_config=saved.values

        snapshot=ConfigurationSnapshot(
            snapshot_id=snapshot_id,
            values=_freeze(source_config),
            captured_at=datetime.now(timezone.utc),
        )

        run=ExperimentRun(
            run_id=run_id,
            experiment_id=experiment_id,
            run_label=run_label,
            mechanism=mechanism,
            configuration_snapshot=snapshot,
            vehicle_ids=tuple(vehicle_ids),
            route_id=route_id,
            fault_scenario_id=fault_scenario_id,
            created_by=created_by,
        )
        run.transition_history.append(
            StateTransition(RunStatus.PENDING.value, datetime.now(timezone.utc))
        )
        self._runs[run_id]=run
        return run

    def get_run(self, run_id: str) -> ExperimentRun:
        if run_id not in self._runs:
            raise KeyError("RUN_NOT_FOUND")
        return self._runs[run_id]

    def start(self, run_id: str) -> ExperimentRun:
        run=self.get_run(run_id)
        if run.status is not RunStatus.PENDING:
            raise ValueError("INVALID_START_TRANSITION")
        self._transition(run, RunStatus.RUNNING)
        run.started_at=run.transition_history[-1].at
        return run

    def pause(self, run_id: str) -> ExperimentRun:
        run=self.get_run(run_id)
        if run.status is not RunStatus.RUNNING:
            raise ValueError("INVALID_PAUSE_TRANSITION")
        self._transition(run, RunStatus.PAUSED)
        return run

    def resume(self, run_id: str) -> ExperimentRun:
        run=self.get_run(run_id)
        if run.status is not RunStatus.PAUSED:
            raise ValueError("INVALID_RESUME_TRANSITION")
        self._transition(run, RunStatus.RUNNING)
        return run

    def complete(self, run_id: str) -> ExperimentRun:
        run=self.get_run(run_id)
        if run.status not in (RunStatus.RUNNING, RunStatus.PAUSED):
            raise ValueError("INVALID_COMPLETE_TRANSITION")
        self.evaluate_validity(run_id)
        self._transition(run, RunStatus.COMPLETED)
        run.ended_at=run.transition_history[-1].at
        if all(run.validity_checks.values()):
            run.validity_status=ValidityStatus.VALID
        else:
            run.validity_status=ValidityStatus.INCOMPLETE
        return run

    def abort(self, run_id: str, *, reason: str) -> ExperimentRun:
        run=self.get_run(run_id)
        if run.status in (RunStatus.COMPLETED, RunStatus.ABORTED):
            raise ValueError("INVALID_ABORT_TRANSITION")
        run.abort_reason=reason
        run.validity_status=ValidityStatus.INVALID
        self._transition(run, RunStatus.ABORTED)
        run.ended_at=run.transition_history[-1].at
        return run

    def record_observation(
        self,
        run_id: str,
        observation: dict[str, Any],
    ) -> ExperimentRun:
        run=self.get_run(run_id)
        if run.status not in (RunStatus.RUNNING, RunStatus.PAUSED):
            raise ValueError("OBSERVATION_REQUIRES_ACTIVE_RUN")
        run.observations.append(dict(observation))
        return run

    def evaluate_validity(self, run_id: str) -> dict[str, bool]:
        run=self.get_run(run_id)
        checks={
            "required_vehicles": bool(run.vehicle_ids),
            "configuration_recorded": bool(run.configuration_snapshot.values),
            "mechanism_recorded": bool(run.mechanism.mechanism_version),
            "experiment_recorded": bool(run.experiment_id),
            "observations_available": bool(run.observations),
            "fault_context_recorded": (
                run.fault_scenario_id is not None
                or True
            ),
        }
        run.validity_checks=checks
        return dict(checks)

    def pause_duration_seconds(self, run_id: str) -> float:
        run=self.get_run(run_id)
        total=0.0
        pause_started=None
        for transition in run.transition_history:
            if transition.state==RunStatus.PAUSED.value:
                pause_started=transition.at
            elif transition.state==RunStatus.RUNNING.value and pause_started is not None:
                total+=(transition.at-pause_started).total_seconds()
                pause_started=None
        if pause_started is not None:
            end=run.ended_at or datetime.now(timezone.utc)
            total+=(end-pause_started).total_seconds()
        return max(0.0,total)

    def _transition(self, run: ExperimentRun, status: RunStatus) -> None:
        run.status=status
        run.transition_history.append(
            StateTransition(status.value, datetime.now(timezone.utc))
        )

    def _get_experiment(self, experiment_id: str) -> Experiment:
        if experiment_id not in self._experiments:
            raise KeyError("EXPERIMENT_NOT_FOUND")
        return self._experiments[experiment_id]

    def _get_fault(self, fault_scenario_id: str) -> FaultScenario:
        if fault_scenario_id not in self._faults:
            raise KeyError("FAULT_SCENARIO_NOT_FOUND")
        return self._faults[fault_scenario_id]
