"""add device authentication to vehicles

Revision ID: 8c1e6d4b2a90
Revises: 7a2d9e4c1f80
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "8c1e6d4b2a90"
down_revision = "7a2d9e4c1f80"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = {
        column["name"]
        for column in inspector.get_columns("vehicles")
    }

    if "device_auth_enabled" not in existing:
        op.add_column(
            "vehicles",
            sa.Column(
                "device_auth_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )

    if "device_secret_hash" not in existing:
        op.add_column(
            "vehicles",
            sa.Column(
                "device_secret_hash",
                sa.String(length=256),
                nullable=True,
            ),
        )

    if "device_secret_salt" not in existing:
        op.add_column(
            "vehicles",
            sa.Column(
                "device_secret_salt",
                sa.String(length=128),
                nullable=True,
            ),
        )

    if "device_secret_version" not in existing:
        op.add_column(
            "vehicles",
            sa.Column(
                "device_secret_version",
                sa.Integer(),
                nullable=False,
                server_default="1",
            ),
        )

    if "device_last_authenticated_at" not in existing:
        op.add_column(
            "vehicles",
            sa.Column(
                "device_last_authenticated_at",
                sa.DateTime(),
                nullable=True,
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = {
        column["name"]
        for column in inspector.get_columns("vehicles")
    }

    if "device_last_authenticated_at" in existing:
        op.drop_column("vehicles", "device_last_authenticated_at")

    if "device_secret_version" in existing:
        op.drop_column("vehicles", "device_secret_version")

    if "device_secret_salt" in existing:
        op.drop_column("vehicles", "device_secret_salt")

    if "device_secret_hash" in existing:
        op.drop_column("vehicles", "device_secret_hash")

    if "device_auth_enabled" in existing:
        op.drop_column("vehicles", "device_auth_enabled")
