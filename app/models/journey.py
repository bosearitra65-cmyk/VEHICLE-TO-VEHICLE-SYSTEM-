from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Journey(Base):
    __tablename__ = "journeys"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    journey_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    convoy_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    origin: Mapped[str] = mapped_column(String(500), nullable=False)
    destination: Mapped[str] = mapped_column(String(500), nullable=False)
    route_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    planned_start_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_start_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
