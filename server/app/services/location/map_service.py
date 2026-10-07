from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.vehicle import Vehicle
from app.models.vehicle_state import VehicleState
from app.models.convoy_member import ConvoyMember
from app.models.journey import Journey
from app.services.route_progress.service import (
    calculate_vehicle_route_progress,
)


@dataclass
class MapVehicle:
    vehicle_id: str
    latitude: float | None
    longitude: float | None
    heading: float | None
    speed: float | None
    communication_status: str | None
    last_update: datetime | None
    convoy_id: str | None
    convoy_role: str | None
    journey_id: str | None
    route_id: str | None
    current_stop: dict[str, Any] | None
    next_stop: dict[str, Any] | None
    route_deviation_status: str | None

    def to_dict(self):
        return asdict(self)


def _active_membership(db: Session, vehicle_id: str):
    return (
        db.query(ConvoyMember)
        .filter(
            ConvoyMember.vehicle_id == vehicle_id,
            ConvoyMember.status == "active",
            ConvoyMember.left_at.is_(None),
        )
        .order_by(ConvoyMember.joined_at.desc())
        .first()
    )


def _active_journey(db: Session, convoy_id: str | None):
    if not convoy_id:
        return None

    return (
        db.query(Journey)
        .filter(
            Journey.convoy_id == convoy_id,
            Journey.status.in_(["planned", "ready", "active", "paused"]),
        )
        .order_by(Journey.created_at.desc())
        .first()
    )


def build_map_vehicle(db: Session, vehicle_id: str) -> MapVehicle:
    state = (
        db.query(VehicleState)
        .filter(VehicleState.vehicle_id == vehicle_id)
        .first()
    )

    membership = _active_membership(db, vehicle_id)

    convoy_id = membership.convoy_id if membership else None
    convoy_role = membership.role if membership else None

    journey = _active_journey(db, convoy_id)
    journey_id = journey.journey_id if journey else None
    route_id = journey.route_id if journey else None

    current_stop = None
    next_stop = None
    deviation_status = None

    if state and route_id:
        try:
            progress = calculate_vehicle_route_progress(db, vehicle_id)

            if progress.current_stop_id:
                current_stop = {
                    "stop_id": progress.current_stop_id,
                    "name": progress.current_stop_name,
                }

            if progress.next_stop_id:
                next_stop = {
                    "stop_id": progress.next_stop_id,
                    "name": progress.next_stop_name,
                }

            deviation_status = progress.deviation_status
        except Exception:
            # Map representation must remain available even if
            # optional route-progress enrichment is temporarily unavailable.
            deviation_status = None

    return MapVehicle(
        vehicle_id=vehicle_id,
        latitude=state.latitude if state else None,
        longitude=state.longitude if state else None,
        heading=getattr(state, "heading", None) if state else None,
        speed=getattr(state, "speed", None) if state else None,
        communication_status=(
            getattr(state, "communication_status", None)
            if state else None
        ),
        last_update=(
            getattr(state, "received_at", None)
            or getattr(state, "updated_at", None)
            if state else None
        ),
        convoy_id=convoy_id,
        convoy_role=convoy_role,
        journey_id=journey_id,
        route_id=route_id,
        current_stop=current_stop,
        next_stop=next_stop,
        route_deviation_status=deviation_status,
    )


def list_map_vehicles(db: Session) -> list[dict]:
    vehicles = (
        db.query(Vehicle)
        .filter(Vehicle.is_active.is_(True))
        .order_by(Vehicle.vehicle_id)
        .all()
    )

    return [
        build_map_vehicle(db, vehicle.vehicle_id).to_dict()
        for vehicle in vehicles
    ]
