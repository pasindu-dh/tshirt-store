"""add order audit events

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-11-04 16:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9e0f1a2b3c4"
down_revision: Union[str, Sequence[str], None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "order_audit_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column(
            "actor_user_id", sa.Integer(), nullable=True
        ),
        sa.Column(
            "action", sa.String(length=30), nullable=False
        ),
        sa.Column(
            "changes",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table(
        "order_audit_events", schema=None
    ) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_order_audit_events_order_id"),
            ["order_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_order_audit_events_created_at"),
            ["created_at"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table(
        "order_audit_events", schema=None
    ) as batch_op:
        batch_op.drop_index(
            batch_op.f("ix_order_audit_events_created_at")
        )
        batch_op.drop_index(
            batch_op.f("ix_order_audit_events_order_id")
        )

    op.drop_table("order_audit_events")
