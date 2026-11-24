
"""repair vehicle session sequence tracking

Revision ID: e2a9e044a0a8
Revises: c84b2a7d901e
"""

from alembic import op
import sqlalchemy as sa


revision = "e2a9e044a0a8"
down_revision = "c84b2a7d901e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vehicle_sessions",
        sa.Column("last_sequence_number", sa.Integer(), nullable=True),
    )

    op.add_column(
        "vehicle_sessions",
        sa.Column("last_payload_hash", sa.String(64), nullable=True),
    )

    op.add_column(
        "vehicle_history",
        sa.Column("payload_hash", sa.String(64), nullable=True),
    )

    op.execute(sa.text("""
        UPDATE vehicle_sessions
        SET last_sequence_number = (
            SELECT MAX(h.sequence_number)
            FROM vehicle_history AS h
            WHERE h.vehicle_id = vehicle_sessions.vehicle_id
              AND h.boot_id = vehicle_sessions.boot_id
        )
        WHERE last_sequence_number IS NULL
    """))

    op.create_index(
        "uq_vehicle_history_session_sequence",
        "vehicle_history",
        ["vehicle_id", "device_id", "boot_id", "sequence_number"],
        unique=True,
        sqlite_where=sa.text(
            "device_id IS NOT NULL AND boot_id IS NOT NULL"
        ),
        postgresql_where=sa.text(
            "device_id IS NOT NULL AND boot_id IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_vehicle_history_session_sequence",
        table_name="vehicle_history",
    )

    op.drop_column("vehicle_history", "payload_hash")
    op.drop_column("vehicle_sessions", "last_payload_hash")
    op.drop_column("vehicle_sessions", "last_sequence_number")
