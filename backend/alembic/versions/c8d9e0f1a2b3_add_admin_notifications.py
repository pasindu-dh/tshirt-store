"""add admin notifications

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-11-04 15:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "admin_notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "notification_type",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "title", sa.String(length=160), nullable=False
        ),
        sa.Column(
            "message", sa.String(length=500), nullable=False
        ),
        sa.Column(
            "link",
            sa.String(length=200),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "is_read",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "read_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table(
        "admin_notifications", schema=None
    ) as batch_op:
        batch_op.create_index(
            batch_op.f(
                "ix_admin_notifications_notification_type"
            ),
            ["notification_type"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_admin_notifications_is_read"),
            ["is_read"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_admin_notifications_created_at"),
            ["created_at"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table(
        "admin_notifications", schema=None
    ) as batch_op:
        batch_op.drop_index(
            batch_op.f("ix_admin_notifications_created_at")
        )
        batch_op.drop_index(
            batch_op.f("ix_admin_notifications_is_read")
        )
        batch_op.drop_index(
            batch_op.f(
                "ix_admin_notifications_notification_type"
            )
        )

    op.drop_table("admin_notifications")
