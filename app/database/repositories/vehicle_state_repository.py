from datetime import datetime

from sqlalchemy.orm import Session

from app.models.vehicle_state import VehicleState


class VehicleStateRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_vehicle_id(
        self,
        vehicle_id: str,
    ) -> VehicleState | None:
        return (
            self.db.query(VehicleState)
            .filter(VehicleState.vehicle_id == vehicle_id)
            .first()
        )

    def create(
        self,
        vehicle_id: str,
        sequence_number: int,
        timestamp: datetime,
        latitude: float,
        longitude: float,
        speed: float,
        heading: float,
        communication_status: str,
        device_id: str | None = None,
        boot_id: str | None = None,
        gps_fix: bool | None = None,
        satellites: int | None = None,
        hdop: float | None = None,
        gps_source: str | None = None,
        transport: str | None = None,
        convoy_id: str | None = None,
        role: str | None = None,
    ) -> VehicleState:
        state = VehicleState(
            vehicle_id=vehicle_id,
            sequence_number=sequence_number,
            timestamp=timestamp,
            latitude=latitude,
            longitude=longitude,
            speed=speed,
            heading=heading,
            communication_status=communication_status,
            device_id=device_id,
            boot_id=boot_id,
            gps_fix=gps_fix,
            satellites=satellites,
            hdop=hdop,
            gps_source=gps_source,
            transport=transport,
            convoy_id=convoy_id,
            role=role,
        )

        self.db.add(state)
        self.db.flush()
        self.db.refresh(state)

        return state
