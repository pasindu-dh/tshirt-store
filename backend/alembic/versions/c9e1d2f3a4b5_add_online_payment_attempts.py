"""add online payment attempts

Revision ID: c9e1d2f3a4b5
Revises: b7d9e1f2a3c4
Create Date: 2026-11-04 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9e1d2f3a4b5"
down_revision: Union[str, Sequence[str], None] = "b7d9e1f2a3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("reference", sa.String(length=100), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "provider_payment_id",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column(
            "paid_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("payments", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_payments_order_id"),
            ["order_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_payments_reference"),
            ["reference"],
            unique=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("payments", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_payments_reference"))
        batch_op.drop_index(batch_op.f("ix_payments_order_id"))

    op.drop_table("payments")
