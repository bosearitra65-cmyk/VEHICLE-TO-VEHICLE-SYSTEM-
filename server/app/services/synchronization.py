
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.auth.authorization import has_permission
from app.auth.permissions import Permission
from app.models.alert import Alert
from app.models.convoy import Convoy
from app.models.event import Event
from app.models.journey import Journey
from app.models.route import Route
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.vehicle_state import VehicleState


def _serialize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, list):
        return [_serialize(item) for item in value]

    if isinstance(value, dict):
        return {
            str(key): _serialize(item)
            for key, item in value.items()
        }

    return value


def _model_dict(obj: Any) -> dict[str, Any]:
    result = {}

    for key, value in obj.__dict__.items():
        if key.startswith("_"):
            continue

        result[key] = _serialize(value)

    return result


def _allowed(user: User, permission: Permission) -> bool:
    return has_permission(user, permission)


def build_sync_state(
    db: Session,
    user: User,
    connection_state: str = "LIVE",
) -> dict[str, Any]:

    result: dict[str, Any] = {
        "server_time": datetime.now(timezone.utc).isoformat(),
        "connection_state": connection_state,
        "authoritative_source": "backend_database",
        "synchronization_mode": "FULL_AUTHORITATIVE",
        "vehicles": [],
        "vehicle_states": [],
        "convoys": [],
        "journeys": [],
        "routes": [],
        "alerts": [],
        "recent_events": [],
    }

    if _allowed(user, Permission.VEHICLE_VIEW):
        result["vehicles"] = [
            _model_dict(item)
            for item in db.query(Vehicle)
            .order_by(Vehicle.id.asc())
            .all()
        ]

        result["vehicle_states"] = [
            _model_dict(item)
            for item in db.query(VehicleState)
            .order_by(VehicleState.vehicle_id.asc())
            .all()
        ]

    if _allowed(user, Permission.CONVOY_VIEW):
        result["convoys"] = [
            _model_dict(item)
            for item in db.query(Convoy)
            .order_by(Convoy.id.asc())
            .all()
        ]

    if _allowed(user, Permission.JOURNEY_VIEW):
        result["journeys"] = [
            _model_dict(item)
            for item in db.query(Journey)
            .order_by(Journey.id.asc())
            .all()
        ]

    if _allowed(user, Permission.ROUTE_VIEW):
        result["routes"] = [
            _model_dict(item)
            for item in db.query(Route)
            .order_by(Route.id.asc())
            .all()
        ]

    if _allowed(user, Permission.ALERTS_VIEW):
        result["alerts"] = [
            _model_dict(item)
            for item in db.query(Alert)
            .filter(Alert.is_active == True)
            .order_by(Alert.id.asc())
            .all()
        ]

    if _allowed(user, Permission.EVENTS_VIEW):
        result["recent_events"] = [
            _model_dict(item)
            for item in db.query(Event)
            .order_by(Event.id.desc())
            .limit(50)
            .all()
        ]

    return result
