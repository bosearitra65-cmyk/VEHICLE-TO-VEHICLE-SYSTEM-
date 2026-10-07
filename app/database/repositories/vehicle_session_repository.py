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
        self.db.refresh(session)
        return session

    def deactivate(
        self,
        session: VehicleSession,
    ) -> VehicleSession:
        session.is_active = False
        self.db.flush()
        self.db.refresh(session)
        return session

    def create(
        self,
        vehicle_id: str,
        boot_id: str,
        started_at: datetime,
        last_seen_at: datetime,
    ) -> VehicleSession:
        session = VehicleSession(
            vehicle_id=vehicle_id,
            boot_id=boot_id,
            started_at=started_at,
            last_seen_at=last_seen_at,
            is_active=True,
        )

        self.db.add(session)
        self.db.flush()
        self.db.refresh(session)

        return session
