from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    vehicle_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    device_id: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        index=True,
    )

    device_auth_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    device_secret_hash: Mapped[str | None] = mapped_column(
        String(256), nullable=True
    )

    device_secret_salt: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )

    device_secret_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )

    device_last_authenticated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )