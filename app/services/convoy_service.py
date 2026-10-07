from sqlalchemy.orm import Session

from app.database.repositories.convoy_member_repository import ConvoyMemberRepository
from app.database.repositories.convoy_repository import ConvoyRepository
from app.models.convoy import Convoy
from app.models.convoy_member import ConvoyMember


class ConvoyService:
    def __init__(self, db: Session):
        self.db = db
        self.convoy_repository = ConvoyRepository(db)
        self.member_repository = ConvoyMemberRepository(db)

    def create_convoy(
        self,
        convoy_id: str,
        name: str,
        status: str,
        leader_vehicle_id: str | None = None,
        journey_id: str | None = None,
        route_id: str | None = None,
    ) -> Convoy:
        existing = self.convoy_repository.get_by_convoy_id(convoy_id)

        if existing is not None:
            raise ValueError("Convoy already exists")

        return self.convoy_repository.create(
            convoy_id=convoy_id,
            name=name,
            status=status,
            leader_vehicle_id=leader_vehicle_id,
            journey_id=journey_id,
            route_id=route_id,
        )

    def get_convoy(
        self,
        convoy_id: str,
    ) -> Convoy | None:
        return self.convoy_repository.get_by_convoy_id(convoy_id)

    def list_convoys(self) -> list[Convoy]:
        return self.convoy_repository.list_all()

    def add_member(
        self,
        convoy_id: str,
        vehicle_id: str,
        role: str,
        status: str = "active",
    ) -> ConvoyMember:
        convoy = self.convoy_repository.get_by_convoy_id(convoy_id)

        if convoy is None:
            raise ValueError("Convoy not found")

        existing = self.member_repository.get_member(
            convoy_id=convoy_id,
            vehicle_id=vehicle_id,
        )

        if existing is not None and existing.status == "active":
            raise ValueError("Vehicle is already an active convoy member")

        return self.member_repository.add_member(
            convoy_id=convoy_id,
            vehicle_id=vehicle_id,
            role=role,
            status=status,
        )

    def list_members(
        self,
        convoy_id: str,
        active_only: bool = False,
    ) -> list[ConvoyMember]:
        convoy = self.convoy_repository.get_by_convoy_id(convoy_id)

        if convoy is None:
            raise ValueError("Convoy not found")

        return self.member_repository.list_members(
            convoy_id=convoy_id,
            active_only=active_only,
        )

    def remove_member(
        self,
        convoy_id: str,
        vehicle_id: str,
    ) -> ConvoyMember:
        member = self.member_repository.get_member(
            convoy_id=convoy_id,
            vehicle_id=vehicle_id,
        )

        if member is None:
            raise ValueError("Convoy member not found")

        if member.status != "active":
            raise ValueError("Convoy member is not active")

        return self.member_repository.remove_member(member)

    def update_leader(
        self,
        convoy_id: str,
        leader_vehicle_id: str | None,
    ) -> Convoy:
        convoy = self.convoy_repository.get_by_convoy_id(convoy_id)

        if convoy is None:
            raise ValueError("Convoy not found")

        return self.convoy_repository.update_leader(
            convoy=convoy,
            leader_vehicle_id=leader_vehicle_id,
        )

    def update_status(
        self,
        convoy_id: str,
        status: str,
    ) -> Convoy:
        convoy = self.convoy_repository.get_by_convoy_id(convoy_id)

        if convoy is None:
            raise ValueError("Convoy not found")

        return self.convoy_repository.update_status(
            convoy=convoy,
            status=status,
        )
