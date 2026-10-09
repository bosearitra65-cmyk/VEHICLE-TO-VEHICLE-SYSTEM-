"""add persistent research experiment and run records

Revision ID: c84b2a7d901e
Revises: a71c4e8d2f10
"""

from alembic import op
import sqlalchemy as sa


revision = "c84b2a7d901e"
down_revision = "a71c4e8d2f10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_experiments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("experiment_id", sa.String(length=100), nullable=False, unique=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("research_question", sa.Text(), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="DRAFT"),
        sa.Column("configuration", sa.JSON(), nullable=True),
        sa.Column("configuration_version", sa.String(length=100), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_research_experiments_experiment_id", "research_experiments", ["experiment_id"], unique=True)

    op.create_table(
        "research_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=100), nullable=False, unique=True),
        sa.Column("experiment_id", sa.String(length=100), sa.ForeignKey("research_experiments.experiment_id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_label", sa.String(length=200), nullable=False),
        sa.Column("mechanism_type", sa.String(length=20), nullable=False),
        sa.Column("mechanism_version", sa.String(length=100), nullable=False),
        sa.Column("snapshot_id", sa.String(length=100), nullable=False),
        sa.Column("configuration_snapshot", sa.JSON(), nullable=False),
        sa.Column("vehicle_ids", sa.JSON(), nullable=False),
        sa.Column("route_id", sa.String(length=100), nullable=True),
        sa.Column("fault_scenario_id", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("validity_status", sa.String(length=20), nullable=False, server_default="INCOMPLETE"),
        sa.Column("abort_reason", sa.Text(), nullable=True),
        sa.Column("observations", sa.JSON(), nullable=False),
        sa.Column("transition_history", sa.JSON(), nullable=False),
        sa.Column("validity_checks", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_research_runs_run_id", "research_runs", ["run_id"], unique=True)
    op.create_index("ix_research_runs_experiment_id", "research_runs", ["experiment_id"])
    op.create_index("ix_research_runs_mechanism_type", "research_runs", ["mechanism_type"])


def downgrade() -> None:
    op.drop_index("ix_research_runs_mechanism_type", table_name="research_runs")
    op.drop_index("ix_research_runs_experiment_id", table_name="research_runs")
    op.drop_index("ix_research_runs_run_id", table_name="research_runs")
    op.drop_table("research_runs")
    op.drop_index("ix_research_experiments_experiment_id", table_name="research_experiments")
    op.drop_table("research_experiments")
