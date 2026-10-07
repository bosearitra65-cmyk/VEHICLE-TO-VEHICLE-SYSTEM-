"""create route stops

Revision ID: 7a2d9e4c1f80
Revises: 5f4a8c1d7b21
Create Date: 2026-10-06
"""

from alembic import op
import sqlalchemy as sa


revision = "7a2d9e4c1f80"
down_revision = "5f4a8c1d7b21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "route_stops",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("stop_id", sa.String(length=100), nullable=False),
        sa.Column("route_id", sa.String(length=100), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("planned_arrival", sa.DateTime(), nullable=True),
        sa.Column("planned_departure", sa.DateTime(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="planned",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["route_id"],
            ["routes.route_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stop_id"),
    )

    op.create_index(
        "ix_route_stops_stop_id",
        "route_stops",
        ["stop_id"],
        unique=False,
    )

    op.create_index(
        "ix_route_stops_route_id",
        "route_stops",
        ["route_id"],
        unique=False,
    )

    op.create_index(
        "ix_route_stops_route_sequence",
        "route_stops",
        ["route_id", "sequence"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_route_stops_route_sequence",
        table_name="route_stops",
    )

    op.drop_index(
        "ix_route_stops_route_id",
        table_name="route_stops",
    )

    op.drop_index(
        "ix_route_stops_stop_id",
        table_name="route_stops",
    )

    op.drop_table("route_stops")
