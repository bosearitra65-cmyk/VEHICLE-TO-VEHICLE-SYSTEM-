from datetime import datetime
from pydantic import BaseModel, Field


# -------------------------
# Vehicles
# -------------------------

class VehicleCreate(BaseModel):
    vehicle_id: str = Field(min_length=1, max_length=100)
    device_id: str | None = Field(default=None, max_length=100)
    name: str | None = Field(default=None, max_length=150)


class VehicleUpdate(BaseModel):
    device_id: str | None = Field(default=None, max_length=100)
    name: str | None = Field(default=None, max_length=150)
    is_active: bool | None = None


class VehicleOut(BaseModel):
    id: int
    vehicle_id: str
    device_id: str | None
    name: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# -------------------------
# Convoys
# -------------------------

class ConvoyCreate(BaseModel):
    convoy_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    status: str = Field(min_length=1, max_length=50)
    leader_vehicle_id: str | None = Field(default=None, max_length=100)
    journey_id: str | None = Field(default=None, max_length=100)
    route_id: str | None = Field(default=None, max_length=100)


class ConvoyUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    status: str | None = Field(default=None, max_length=50)
    leader_vehicle_id: str | None = Field(default=None, max_length=100)
    journey_id: str | None = Field(default=None, max_length=100)
    route_id: str | None = Field(default=None, max_length=100)


class ConvoyOut(BaseModel):
    id: int
    convoy_id: str
    name: str
    status: str
    leader_vehicle_id: str | None
    journey_id: str | None
    route_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConvoyMemberCreate(BaseModel):
    vehicle_id: str = Field(min_length=1, max_length=100)
    role: str = Field(min_length=1, max_length=50)
    status: str = Field(default="active", min_length=1, max_length=50)


class ConvoyMemberOut(BaseModel):
    id: int
    convoy_id: str
    vehicle_id: str
    role: str
    joined_at: datetime
    left_at: datetime | None
    status: str

    model_config = {"from_attributes": True}


class LeaderUpdate(BaseModel):
    vehicle_id: str = Field(min_length=1, max_length=100)


# -------------------------
# Journeys
# -------------------------

class JourneyCreate(BaseModel):
    journey_id: str = Field(min_length=1, max_length=100)
    convoy_id: str = Field(min_length=1, max_length=100)
    origin: str = Field(min_length=1, max_length=500)
    destination: str = Field(min_length=1, max_length=500)
    route_id: str | None = Field(default=None, max_length=100)
    status: str = Field(default="planned", min_length=1, max_length=50)
    planned_start_at: datetime | None = None
    created_by: str | None = Field(default=None, max_length=100)


class JourneyUpdate(BaseModel):
    origin: str | None = Field(default=None, max_length=500)
    destination: str | None = Field(default=None, max_length=500)
    planned_start_at: datetime | None = None


class JourneyOut(BaseModel):
    id: int
    journey_id: str
    convoy_id: str
    origin: str
    destination: str
    route_id: str | None
    status: str
    planned_start_at: datetime | None
    actual_start_at: datetime | None
    completed_at: datetime | None
    created_by: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# -------------------------
# Routes
# -------------------------

class RouteCreate(BaseModel):
    route_id: str = Field(min_length=1, max_length=100)
    origin: str = Field(min_length=1, max_length=500)
    destination: str = Field(min_length=1, max_length=500)
    geometry: str = Field(min_length=1)
    distance: float | None = None
    estimated_duration: int | None = None
    created_by: str | None = Field(default=None, max_length=100)
    version: int = Field(default=1, ge=1)


class RouteCalculate(BaseModel):
    origin: str = Field(min_length=1, max_length=500)
    destination: str = Field(min_length=1, max_length=500)


class RouteOut(BaseModel):
    id: int
    route_id: str
    origin: str
    destination: str
    geometry: str
    distance: float | None
    estimated_duration: int | None
    created_at: datetime
    created_by: str | None
    version: int

    model_config = {"from_attributes": True}


# -------------------------
# Events
# -------------------------

class EventOut(BaseModel):
    id: int
    vehicle_id: str
    event_type: str
    severity: str
    sequence_number: int | None
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}


# -------------------------
# Alerts
# -------------------------

class AlertOut(BaseModel):
    id: int
    vehicle_id: str
    alert_type: str
    severity: str
    message: str
    source_event_id: int | None
    is_active: bool
    created_at: datetime
    resolved_at: datetime | None

    model_config = {"from_attributes": True}

class RouteStopCreate(BaseModel):
    stop_id: str = Field(min_length=1, max_length=100)
    sequence: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    planned_arrival: datetime | None = None
    planned_departure: datetime | None = None
    actual_arrival_at: datetime | None = None
    actual_departure_at: datetime | None = None
    status: str = Field(default="planned", min_length=1, max_length=50)


class RouteStopOut(BaseModel):
    id: int
    stop_id: str
    route_id: str
    sequence: int
    name: str
    latitude: float
    longitude: float
    planned_arrival: datetime | None
    planned_departure: datetime | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}

