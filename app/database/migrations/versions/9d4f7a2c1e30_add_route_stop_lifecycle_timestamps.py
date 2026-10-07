"""add route stop lifecycle timestamps

Revision ID: 9d4f7a2c1e30
Revises: 8c1e6d4b2a90
"""

from alembic import op
import sqlalchemy as sa


revision = "9d4f7a2c1e30"
down_revision = "8c1e6d4b2a90"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {
        column["name"]
        for column in inspector.get_columns("route_stops")
    }

    if "actual_arrival_at" not in columns:
        op.add_column(
            "route_stops",
            sa.Column(
                "actual_arrival_at",
                sa.DateTime(),
                nullable=True,
            ),
        )

    if "actual_departure_at" not in columns:
        op.add_column(
            "route_stops",
            sa.Column(
                "actual_departure_at",
                sa.DateTime(),
                nullable=True,
            ),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {
        column["name"]
        for column in inspector.get_columns("route_stops")
    }

    if "actual_departure_at" in columns:
        op.drop_column("route_stops", "actual_departure_at")

    if "actual_arrival_at" in columns:
        op.drop_column("route_stops", "actual_arrival_at")
