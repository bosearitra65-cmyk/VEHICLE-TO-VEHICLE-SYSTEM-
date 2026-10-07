from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class VehicleHistory(Base):
    __tablename__ = "vehicle_history"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    vehicle_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
    )

    latitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    speed: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    heading: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    communication_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    device_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    boot_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    gps_fix: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    satellites: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    hdop: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    gps_source: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    transport: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    convoy_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    role: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )
