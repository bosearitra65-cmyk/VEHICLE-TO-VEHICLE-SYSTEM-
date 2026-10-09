from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ResearchExperimentRecord(Base):
    __tablename__ = "research_experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    research_question: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    configuration: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    configuration_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ResearchRunRecord(Base):
    __tablename__ = "research_runs"
    __table_args__ = (
        Index("ix_research_runs_experiment_id", "experiment_id"),
        Index("ix_research_runs_mechanism_type", "mechanism_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    experiment_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("research_experiments.experiment_id", ondelete="CASCADE"),
        nullable=False,
    )
    run_label: Mapped[str] = mapped_column(String(200), nullable=False)
    mechanism_type: Mapped[str] = mapped_column(String(20), nullable=False)
    mechanism_version: Mapped[str] = mapped_column(String(100), nullable=False)
    snapshot_id: Mapped[str] = mapped_column(String(100), nullable=False)
    configuration_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    vehicle_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    route_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fault_scenario_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    validity_status: Mapped[str] = mapped_column(String(20), nullable=False, default="INCOMPLETE")
    abort_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    observations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    transition_history: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    validity_checks: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
