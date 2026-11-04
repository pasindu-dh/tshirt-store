"""add return policy fields

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
Create Date: 2026-11-04 15:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "a6b7c8d9e0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "delivered_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )

    with op.batch_alter_table(
        "return_requests", schema=None
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "reason_code",
                sa.String(length=30),
                nullable=False,
                server_default="other",
            )
        )

    op.execute(
        "UPDATE orders "
        "SET delivered_at = updated_at "
        "WHERE status = 'delivered' "
        "AND delivered_at IS NULL"
    )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table(
        "return_requests", schema=None
    ) as batch_op:
        batch_op.drop_column("reason_code")

    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.drop_column("delivered_at")
