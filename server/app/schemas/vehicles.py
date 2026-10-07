from datetime import datetime

from pydantic import BaseModel, Field


class VehicleStateIn(BaseModel):
    vehicle_id: str = Field(min_length=1, max_length=100)
    sequence_number: int = Field(ge=0)
    timestamp: datetime

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    speed: float = Field(ge=0)
    heading: float = Field(ge=0, lt=360)

    communication_status: str = Field(min_length=1, max_length=50)

    device_id: str | None = Field(default=None, max_length=100)
    boot_id: str | None = Field(default=None, max_length=100)

    gps_fix: bool | None = None
    satellites: int | None = Field(default=None, ge=0)
    hdop: float | None = Field(default=None, gt=0)

    gps_source: str | None = Field(default=None, max_length=50)
    transport: str | None = Field(default=None, max_length=50)

    convoy_id: str | None = Field(default=None, max_length=100)
    role: str | None = Field(default=None, max_length=50)

class VehicleStateOut(BaseModel):
    vehicle_id: str
    sequence_number: int
    timestamp: datetime
    latitude: float
    longitude: float
    speed: float
    heading: float
    communication_status: str
    device_id: str | None = None
    boot_id: str | None = None
    gps_fix: bool | None = None
    satellites: int | None = None
    hdop: float | None = None
    gps_source: str | None = None
    transport: str | None = None
    convoy_id: str | None = None
    role: str | None = None
    updated_at: datetime


class VehicleHistoryOut(BaseModel):
    id: int
    vehicle_id: str
    sequence_number: int
    timestamp: datetime
    latitude: float
    longitude: float
    speed: float
    heading: float
    communication_status: str
    device_id: str | None = None
    boot_id: str | None = None
    gps_fix: bool | None = None
    satellites: int | None = None
    hdop: float | None = None
    gps_source: str | None = None
    transport: str | None = None
    convoy_id: str | None = None
    role: str | None = None
    recorded_at: datetime

class VehicleFreshnessOut(BaseModel):
    vehicle_id: str
    sequence_number: int
    timestamp: datetime
    age_seconds: float
    is_fresh: bool


class VehicleAvailabilityOut(BaseModel):
    vehicle_id: str
    sequence_number: int
    age_seconds: float
    is_fresh: bool
    reported_communication_status: str
    availability: str
