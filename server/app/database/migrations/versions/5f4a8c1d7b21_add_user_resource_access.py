"""add user resource access control

Revision ID: 5f4a8c1d7b21
Revises: 2e93dd02cb69
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5f4a8c1d7b21"
down_revision: Union[str, Sequence[str], None] = "2e93dd02cb69"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_resource_access",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("resource_id", sa.String(length=100), nullable=False),
        sa.Column("permission", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "resource_type",
            "resource_id",
            "permission",
            name="uq_user_resource_permission",
        ),
    )

    op.create_index(
        op.f("ix_user_resource_access_user_id"),
        "user_resource_access",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_resource_access_resource_type"),
        "user_resource_access",
        ["resource_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_resource_access_resource_id"),
        "user_resource_access",
        ["resource_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_resource_access_permission"),
        "user_resource_access",
        ["permission"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_resource_access_created_by"),
        "user_resource_access",
        ["created_by"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_user_resource_access_created_by"),
        table_name="user_resource_access",
    )
    op.drop_index(
        op.f("ix_user_resource_access_permission"),
        table_name="user_resource_access",
    )
    op.drop_index(
        op.f("ix_user_resource_access_resource_id"),
        table_name="user_resource_access",
    )
    op.drop_index(
        op.f("ix_user_resource_access_resource_type"),
        table_name="user_resource_access",
    )
    op.drop_index(
        op.f("ix_user_resource_access_user_id"),
        table_name="user_resource_access",
    )
    op.drop_table("user_resource_access")
