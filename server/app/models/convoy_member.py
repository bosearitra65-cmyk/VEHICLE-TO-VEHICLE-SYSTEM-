from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ConvoyMember(Base):
    __tablename__ = "convoy_members"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    convoy_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    vehicle_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    left_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
