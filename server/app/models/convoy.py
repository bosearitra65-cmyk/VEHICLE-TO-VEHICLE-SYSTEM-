from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Convoy(Base):
    __tablename__ = "convoys"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    convoy_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    leader_vehicle_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    journey_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    route_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
