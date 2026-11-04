"""add reservation expiry, payment events, and reconciliation fields

Revision ID: d1e2f3a4b5c6
Revises: c9e1d2f3a4b5
Create Date: 2026-11-04 09:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "c9e1d2f3a4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "reservation_expires_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "stock_released_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "stock_release_reason",
                sa.String(length=30),
                server_default="",
                nullable=False,
            )
        )

    op.create_table(
        "payment_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payment_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "status_code",
            sa.String(length=10),
            server_default="",
            nullable=False,
        ),
        sa.Column(
            "provider_payment_id",
            sa.String(length=100),
            server_default="",
            nullable=False,
        ),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "source",
            sa.String(length=20),
            server_default="",
            nullable=False,
        ),
        sa.Column(
            "note", sa.Text(), server_default="", nullable=False
        ),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"], ["payments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("payment_events", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_payment_events_payment_id"),
            ["payment_id"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("payment_events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_payment_events_payment_id"))

    op.drop_table("payment_events")

    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.drop_column("stock_release_reason")
        batch_op.drop_column("stock_released_at")
        batch_op.drop_column("reservation_expires_at")
