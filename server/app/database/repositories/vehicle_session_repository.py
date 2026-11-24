
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.vehicle_session import VehicleSession


class VehicleSessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active_by_vehicle_and_boot(
        self,
        vehicle_id: str,
        boot_id: str,
    ) -> VehicleSession | None:
        return (
            self.db.query(VehicleSession)
            .filter(
                VehicleSession.vehicle_id == vehicle_id,
                VehicleSession.boot_id == boot_id,
                VehicleSession.is_active.is_(True),
            )
            .first()
        )

    def get_by_vehicle_and_boot(
        self,
        vehicle_id: str,
        boot_id: str,
    ) -> VehicleSession | None:
        return (
            self.db.query(VehicleSession)
            .filter(
                VehicleSession.vehicle_id == vehicle_id,
                VehicleSession.boot_id == boot_id,
            )
            .order_by(VehicleSession.started_at.desc())
            .first()
        )

    def list_active_by_vehicle(
        self,
        vehicle_id: str,
    ) -> list[VehicleSession]:
        return (
            self.db.query(VehicleSession)
            .filter(
                VehicleSession.vehicle_id == vehicle_id,
                VehicleSession.is_active.is_(True),
            )
            .all()
        )

    def update_last_seen(
        self,
        session: VehicleSession,
        last_seen_at: datetime,
    ) -> VehicleSession:
        session.last_seen_at = last_seen_at
        self.db.flush()
        return session

    def update_sequence(
        self,
        session: VehicleSession,
        sequence_number: int,
        payload_hash: str | None = None,
        last_seen_at: datetime | None = None,
    ) -> VehicleSession:
        session.last_sequence_number = sequence_number
        session.last_payload_hash = payload_hash

        if last_seen_at is not None:
            session.last_seen_at = last_seen_at

        self.db.flush()
        return session

    def deactivate(
        self,
        session: VehicleSession,
    ) -> VehicleSession:
        session.is_active = False
        self.db.flush()
        return session

    def create(
        self,
        vehicle_id: str,
        boot_id: str,
        started_at: datetime,
        last_seen_at: datetime,
        last_sequence_number: int | None = None,
        last_payload_hash: str | None = None,
    ) -> VehicleSession:
        session = VehicleSession(
            vehicle_id=vehicle_id,
            boot_id=boot_id,
            started_at=started_at,
            last_seen_at=last_seen_at,
            is_active=True,
            last_sequence_number=last_sequence_number,
            last_payload_hash=last_payload_hash,
        )

        self.db.add(session)
        self.db.flush()
        return session
