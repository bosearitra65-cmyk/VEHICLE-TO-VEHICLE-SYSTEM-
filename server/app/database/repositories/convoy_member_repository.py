from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.convoy_member import ConvoyMember


class ConvoyMemberRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_member(
        self,
        convoy_id: str,
        vehicle_id: str,
        role: str,
        status: str = "active",
    ) -> ConvoyMember:
        member = ConvoyMember(
            convoy_id=convoy_id,
            vehicle_id=vehicle_id,
            role=role,
            status=status,
        )

        self.db.add(member)
        self.db.flush()
        self.db.refresh(member)

        return member

    def get_member(
        self,
        convoy_id: str,
        vehicle_id: str,
    ) -> ConvoyMember | None:
        return (
            self.db.query(ConvoyMember)
            .filter(
                ConvoyMember.convoy_id == convoy_id,
                ConvoyMember.vehicle_id == vehicle_id,
            )
            .order_by(ConvoyMember.id.desc())
            .first()
        )

    def list_members(
        self,
        convoy_id: str,
        active_only: bool = False,
    ) -> list[ConvoyMember]:
        query = (
            self.db.query(ConvoyMember)
            .filter(ConvoyMember.convoy_id == convoy_id)
            .order_by(ConvoyMember.id.asc())
        )

        if active_only:
            query = query.filter(ConvoyMember.status == "active")

        return query.all()

    def remove_member(
        self,
        member: ConvoyMember,
    ) -> ConvoyMember:
        member.status = "inactive"
        member.left_at = datetime.now(timezone.utc).replace(tzinfo=None)

        self.db.flush()
        self.db.refresh(member)

        return member
