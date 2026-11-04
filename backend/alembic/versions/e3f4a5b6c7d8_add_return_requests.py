"""add customer return requests

Revision ID: e3f4a5b6c7d8
Revises: e2f3a4b5c6d7
Create Date: 2026-11-04 11:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "return_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column(
            "notes", sa.Text(), server_default="", nullable=False
        ),
        sa.Column("refund_id", sa.Integer(), nullable=True),
        sa.Column(
            "review_note", sa.Text(), server_default="", nullable=False
        ),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "reviewed_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["refund_id"], ["refunds.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("return_requests", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_return_requests_order_id"),
            ["order_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_return_requests_user_id"),
            ["user_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_return_requests_refund_id"),
            ["refund_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_return_requests_status"),
            ["status"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("return_requests", schema=None) as batch_op:
        batch_op.drop_index(
            batch_op.f("ix_return_requests_status")
        )
        batch_op.drop_index(
            batch_op.f("ix_return_requests_refund_id")
        )
        batch_op.drop_index(
            batch_op.f("ix_return_requests_user_id")
        )
        batch_op.drop_index(
            batch_op.f("ix_return_requests_order_id")
        )

    op.drop_table("return_requests")
