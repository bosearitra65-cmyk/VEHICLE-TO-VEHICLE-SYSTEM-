"""add vehicle display number and convoy role constraints

Revision ID: a71c4e8d2f10
Revises: 9d4f7a2c1e30
"""

from alembic import op
import sqlalchemy as sa


revision = "a71c4e8d2f10"
down_revision = "9d4f7a2c1e30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite-safe strategy:
    # 1. Add the new column temporarily nullable.
    # 2. Backfill stable display numbers using existing vehicle IDs.
    # 3. Use Alembic batch mode to make the column NOT NULL.
    # 4. Add a unique index.
    op.add_column(
        "vehicles",
        sa.Column(
            "display_number",
            sa.Integer(),
            nullable=True,
        ),
    )

    bind = op.get_bind()

    vehicle_ids = bind.execute(
        sa.text(
            "SELECT id FROM vehicles ORDER BY id"
        )
    ).fetchall()

    for number, row in enumerate(vehicle_ids, start=1):
        bind.execute(
            sa.text(
                "UPDATE vehicles "
                "SET display_number = :display_number "
                "WHERE id = :vehicle_id"
            ),
            {
                "display_number": number,
                "vehicle_id": row[0],
            },
        )

    # SQLite does not support:
    # ALTER TABLE ... ALTER COLUMN ... SET NOT NULL
    #
    # Alembic batch mode performs the required SQLite-safe
    # table recreation and preserves existing vehicle data.
    with op.batch_alter_table("vehicles") as batch_op:
        batch_op.alter_column(
            "display_number",
            existing_type=sa.Integer(),
            nullable=False,
        )

    op.create_index(
        "ix_vehicles_display_number",
        "vehicles",
        ["display_number"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_vehicles_display_number",
        table_name="vehicles",
    )

    with op.batch_alter_table("vehicles") as batch_op:
        batch_op.drop_column("display_number")
