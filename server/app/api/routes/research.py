from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_permission
from app.auth.authorization import has_permission
from app.auth.permissions import Permission
from app.models.research_records import ResearchExperimentRecord, ResearchRunRecord
from app.models.route import Route
from app.models.vehicle import Vehicle
from app.models.user import User
from app.schemas.common import APIResponse
from app.utils.identifiers import generate_request_id


router = APIRouter(prefix="/research", tags=["research"])


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def response(data: Any) -> APIResponse:
    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=now_utc(),
        data=data,
    )


def experiment_dict(item: ResearchExperimentRecord) -> dict:
    return {
        "experiment_id": item.experiment_id,
        "name": item.name,
        "research_question": item.research_question,
        "objective": item.objective,
        "description": item.description,
        "status": item.status,
        "configuration": item.configuration,
        "configuration_version": item.configuration_version,
        "created_by": item.created_by,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "started_at": item.started_at,
        "completed_at": item.completed_at,
    }


def run_dict(item: ResearchRunRecord) -> dict:
    return {
        "run_id": item.run_id,
        "experiment_id": item.experiment_id,
        "run_label": item.run_label,
        "mechanism_type": item.mechanism_type,
        "mechanism_version": item.mechanism_version,
        "snapshot_id": item.snapshot_id,
        "configuration_snapshot": item.configuration_snapshot,
        "vehicle_ids": item.vehicle_ids,
        "route_id": item.route_id,
        "fault_scenario_id": item.fault_scenario_id,
        "status": item.status,
        "validity_status": item.validity_status,
        "abort_reason": item.abort_reason,
        "observations": item.observations,
        "transition_history": item.transition_history,
        "validity_checks": item.validity_checks,
        "created_by": item.created_by,
        "created_at": item.created_at,
        "started_at": item.started_at,
        "ended_at": item.ended_at,
    }


class ExperimentCreate(BaseModel):
    experiment_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    research_question: str = Field(min_length=1, max_length=5000)
    objective: str = Field(min_length=1, max_length=5000)
    description: str = Field(default="", max_length=10000)


class ConfigurationUpdate(BaseModel):
    values: dict[str, Any]
    configuration_version: str = Field(default="CONFIG-v1", min_length=1, max_length=100)


class RunCreate(BaseModel):
    run_label: str = Field(min_length=1, max_length=200)
    mechanism_type: str = Field(pattern="^(BASELINE|CANDIDATE)$")
    mechanism_version: str = Field(min_length=1, max_length=100)
    vehicle_ids: list[str] = Field(min_length=1, max_length=100)
    route_id: str | None = Field(default=None, max_length=100)
    fault_scenario_id: str | None = Field(default=None, max_length=100)
    snapshot_id: str | None = Field(default=None, max_length=100)
    configuration_override: dict[str, Any] | None = None


class ObservationCreate(BaseModel):
    observation: dict[str, Any]


class AbortRun(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


@router.get("/experiments")
def list_experiments(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.RESEARCH_VIEW)),
):
    items = db.query(ResearchExperimentRecord).order_by(
        ResearchExperimentRecord.created_at.desc()
    ).limit(500).all()
    return response([experiment_dict(item) for item in items])


@router.post("/experiments", status_code=status.HTTP_201_CREATED)
def create_experiment(
    payload: ExperimentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.RESEARCH_CREATE)),
):
    if db.query(ResearchExperimentRecord).filter_by(
        experiment_id=payload.experiment_id
    ).first():
        raise HTTPException(status_code=409, detail="EXPERIMENT_ID_ALREADY_EXISTS")

    item = ResearchExperimentRecord(
        experiment_id=payload.experiment_id,
        name=payload.name,
        research_question=payload.research_question,
        objective=payload.objective,
        description=payload.description,
        status="DRAFT",
        created_by=str(user.id),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return response(experiment_dict(item))


@router.get("/experiments/{experiment_id}")
def get_experiment(
    experiment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.RESEARCH_VIEW)),
):
    item = db.query(ResearchExperimentRecord).filter_by(
        experiment_id=experiment_id
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="EXPERIMENT_NOT_FOUND")
    return response(experiment_dict(item))


@router.put("/experiments/{experiment_id}/configuration")
def configure_experiment(
    experiment_id: str,
    payload: ConfigurationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.RESEARCH_CONFIGURE)),
):
    item = db.query(ResearchExperimentRecord).filter_by(
        experiment_id=experiment_id
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="EXPERIMENT_NOT_FOUND")
    if item.status != "DRAFT":
        raise HTTPException(status_code=409, detail="CONFIGURATION_LOCKED")
    if not payload.values:
        raise HTTPException(status_code=422, detail="NON_EMPTY_CONFIGURATION_REQUIRED")

    item.configuration = payload.values
    item.configuration_version = payload.configuration_version
    item.updated_at = now_utc()
    db.commit()
    db.refresh(item)
    return response(experiment_dict(item))


@router.post("/experiments/{experiment_id}/ready")
def mark_experiment_ready(
    experiment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.RESEARCH_CONFIGURE)),
):
    item = db.query(ResearchExperimentRecord).filter_by(
        experiment_id=experiment_id
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="EXPERIMENT_NOT_FOUND")
    if item.status != "DRAFT":
        raise HTTPException(status_code=409, detail="INVALID_EXPERIMENT_READY_TRANSITION")
    if not item.configuration or not item.configuration_version:
        raise HTTPException(status_code=409, detail="EXPERIMENT_CONFIGURATION_REQUIRED")
    item.status = "READY"
    item.updated_at = now_utc()
    db.commit()
    db.refresh(item)
    return response(experiment_dict(item))


@router.post("/experiments/{experiment_id}/runs", status_code=status.HTTP_201_CREATED)
def create_run(
    experiment_id: str,
    payload: RunCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.RESEARCH_RUN)),
):
    experiment = db.query(ResearchExperimentRecord).filter_by(
        experiment_id=experiment_id
    ).first()
    if experiment is None:
        raise HTTPException(status_code=404, detail="EXPERIMENT_NOT_FOUND")
    if experiment.status not in ("READY", "RUNNING"):
        raise HTTPException(status_code=409, detail="EXPERIMENT_NOT_READY_FOR_RUN")

    vehicle_ids = [value.strip() for value in payload.vehicle_ids]
    if any(not value for value in vehicle_ids) or len(set(vehicle_ids)) != len(vehicle_ids):
        raise HTTPException(status_code=422, detail="VEHICLE_IDS_MUST_BE_NONEMPTY_AND_UNIQUE")

    vehicles = db.query(Vehicle).filter(Vehicle.vehicle_id.in_(vehicle_ids)).all()
    found_vehicles = {vehicle.vehicle_id: vehicle for vehicle in vehicles}
    missing_vehicles = sorted(set(vehicle_ids) - set(found_vehicles))
    if missing_vehicles:
        raise HTTPException(status_code=422, detail={"code": "UNKNOWN_VEHICLE_IDS", "vehicle_ids": missing_vehicles})
    inactive_vehicles = sorted(vehicle_id for vehicle_id, vehicle in found_vehicles.items() if not vehicle.is_active)
    if inactive_vehicles:
        raise HTTPException(status_code=409, detail={"code": "INACTIVE_VEHICLES", "vehicle_ids": inactive_vehicles})

    if payload.route_id and db.query(Route).filter_by(route_id=payload.route_id).first() is None:
        raise HTTPException(status_code=422, detail="UNKNOWN_ROUTE_ID")

    if payload.fault_scenario_id and not has_permission(user, Permission.RESEARCH_FAULT_CONTROL):
        raise HTTPException(status_code=403, detail="FAULT_CONTROL_PERMISSION_REQUIRED")

    if payload.configuration_override is None:
        configuration = experiment.configuration
    else:
        configuration = payload.configuration_override
    if not configuration:
        raise HTTPException(status_code=409, detail="EXPERIMENT_CONFIGURATION_REQUIRED")

    run_id = str(uuid4())
    timestamp = now_utc()
    snapshot_id = payload.snapshot_id or str(uuid4())
    item = ResearchRunRecord(
        run_id=run_id,
        experiment_id=experiment_id,
        run_label=payload.run_label,
        mechanism_type=payload.mechanism_type,
        mechanism_version=payload.mechanism_version,
        snapshot_id=snapshot_id,
        configuration_snapshot={
            "values": configuration,
            "configuration_version": experiment.configuration_version,
            "route_id": payload.route_id,
            "vehicle_ids": vehicle_ids,
            "fault_scenario_id": payload.fault_scenario_id,
        },
        vehicle_ids=vehicle_ids,
        route_id=payload.route_id,
        fault_scenario_id=payload.fault_scenario_id,
        status="PENDING",
        validity_status="INCOMPLETE",
        observations=[],
        transition_history=[{"state": "PENDING", "at": timestamp.isoformat()}],
        validity_checks={},
        created_by=str(user.id),
        created_at=timestamp,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return response(run_dict(item))


@router.get("/experiments/{experiment_id}/runs")
def list_runs(
    experiment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.RESEARCH_VIEW)),
):
    if db.query(ResearchExperimentRecord).filter_by(
        experiment_id=experiment_id
    ).first() is None:
        raise HTTPException(status_code=404, detail="EXPERIMENT_NOT_FOUND")
    items = db.query(ResearchRunRecord).filter_by(
        experiment_id=experiment_id
    ).order_by(ResearchRunRecord.created_at.asc()).limit(1000).all()
    return response([run_dict(item) for item in items])


@router.get("/runs/{run_id}")
def get_run(
    run_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.RESEARCH_VIEW)),
):
    item = db.query(ResearchRunRecord).filter_by(run_id=run_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="RUN_NOT_FOUND")
    return response(run_dict(item))


def transition_run(item: ResearchRunRecord, target: str) -> None:
    allowed = {
        "start": ({"PENDING"}, "RUNNING"),
        "pause": ({"RUNNING"}, "PAUSED"),
        "resume": ({"PAUSED"}, "RUNNING"),
    }
    expected, next_status = allowed[target]
    if item.status not in expected:
        raise HTTPException(status_code=409, detail=f"INVALID_{target.upper()}_TRANSITION")
    timestamp = now_utc()
    item.status = next_status
    if target == "start":
        item.started_at = timestamp
    item.transition_history = list(item.transition_history or []) + [
        {"state": next_status, "at": timestamp.isoformat()}
    ]


def load_run(db: Session, run_id: str) -> ResearchRunRecord:
    item = db.query(ResearchRunRecord).filter_by(run_id=run_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="RUN_NOT_FOUND")
    return item


@router.post("/runs/{run_id}/start")
def start_run(
    run_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.RESEARCH_RUN)),
):
    item = load_run(db, run_id)
    transition_run(item, "start")
    db.commit()
    db.refresh(item)
    return response(run_dict(item))


@router.post("/runs/{run_id}/pause")
def pause_run(
    run_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.RESEARCH_RUN)),
):
    item = load_run(db, run_id)
    transition_run(item, "pause")
    db.commit()
    db.refresh(item)
    return response(run_dict(item))


@router.post("/runs/{run_id}/resume")
def resume_run(
    run_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.RESEARCH_RUN)),
):
    item = load_run(db, run_id)
    transition_run(item, "resume")
    db.commit()
    db.refresh(item)
    return response(run_dict(item))


@router.post("/runs/{run_id}/observations")
def add_observation(
    run_id: str,
    payload: ObservationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.RESEARCH_RUN)),
):
    item = load_run(db, run_id)
    if item.status not in ("RUNNING", "PAUSED"):
        raise HTTPException(status_code=409, detail="OBSERVATION_REQUIRES_ACTIVE_RUN")
    observation = dict(payload.observation)
    if not observation:
        raise HTTPException(status_code=422, detail="EMPTY_OBSERVATION")
    item.observations = list(item.observations or []) + [
        {"recorded_at": now_utc().isoformat(), "data": observation}
    ]
    db.commit()
    db.refresh(item)
    return response(run_dict(item))


@router.post("/runs/{run_id}/complete")
def complete_run(
    run_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.RESEARCH_RUN)),
):
    item = load_run(db, run_id)
    if item.status not in ("RUNNING", "PAUSED"):
        raise HTTPException(status_code=409, detail="INVALID_COMPLETE_TRANSITION")
    snapshot = item.configuration_snapshot or {}
    current_vehicle_rows = db.query(Vehicle).filter(Vehicle.vehicle_id.in_(item.vehicle_ids or [])).all()
    current_vehicles = {vehicle.vehicle_id: vehicle for vehicle in current_vehicle_rows}
    vehicles_valid = (
        bool(item.vehicle_ids)
        and len(current_vehicles) == len(set(item.vehicle_ids))
        and all(vehicle.is_active for vehicle in current_vehicles.values())
    )
    route_valid = (
        item.route_id is None
        or db.query(Route).filter_by(route_id=item.route_id).first() is not None
    )
    checks = {
        "required_vehicles": bool(item.vehicle_ids),
        "vehicle_references_valid": vehicles_valid,
        "route_reference_valid": route_valid,
        "configuration_recorded": bool(snapshot.get("values")),
        "mechanism_recorded": bool(item.mechanism_version),
        "experiment_recorded": db.query(ResearchExperimentRecord).filter_by(experiment_id=item.experiment_id).first() is not None,
        "observations_available": bool(item.observations),
        "fault_context_recorded": "fault_scenario_id" in snapshot,
    }
    item.validity_checks = checks
    item.validity_status = "VALID" if all(checks.values()) else "INCOMPLETE"
    item.status = "COMPLETED"
    item.ended_at = now_utc()
    item.transition_history = list(item.transition_history or []) + [
        {"state": "COMPLETED", "at": item.ended_at.isoformat()}
    ]
    db.commit()
    db.refresh(item)
    return response(run_dict(item))


@router.post("/runs/{run_id}/abort")
def abort_run(
    run_id: str,
    payload: AbortRun,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.RESEARCH_RUN)),
):
    item = load_run(db, run_id)
    if item.status in ("COMPLETED", "ABORTED"):
        raise HTTPException(status_code=409, detail="INVALID_ABORT_TRANSITION")
    item.status = "ABORTED"
    item.validity_status = "INVALID"
    item.abort_reason = payload.reason
    item.ended_at = now_utc()
    item.transition_history = list(item.transition_history or []) + [
        {"state": "ABORTED", "at": item.ended_at.isoformat()}
    ]
    db.commit()
    db.refresh(item)
    return response(run_dict(item))
