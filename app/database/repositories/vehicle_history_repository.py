from datetime import datetime

from sqlalchemy.orm import Session

from app.models.vehicle_history import VehicleHistory


class VehicleHistoryRepository:
    def __init__(self, db: Session):
        self.db = db

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
    ) -> VehicleHistory:
        history = VehicleHistory(
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

        self.db.add(history)
        self.db.flush()
        self.db.refresh(history)

        return history

    def list_by_vehicle(
        self,
        vehicle_id: str,
    ) -> list[VehicleHistory]:
        return (
            self.db.query(VehicleHistory)
            .filter(VehicleHistory.vehicle_id == vehicle_id)
            .order_by(VehicleHistory.sequence_number.asc())
            .all()
        )

    def list_by_vehicle_and_time(
        self,
        vehicle_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[VehicleHistory]:
        return (
            self.db.query(VehicleHistory)
            .filter(
                VehicleHistory.vehicle_id == vehicle_id,
                VehicleHistory.timestamp >= start_time,
                VehicleHistory.timestamp <= end_time,
            )
            .order_by(VehicleHistory.timestamp.asc())
            .all()
        )

    def get_latest(
        self,
        vehicle_id: str,
    ) -> VehicleHistory | None:
        return (
            self.db.query(VehicleHistory)
            .filter(VehicleHistory.vehicle_id == vehicle_id)
            .order_by(VehicleHistory.sequence_number.desc())
            .first()
        )
