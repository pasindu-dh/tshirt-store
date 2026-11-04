"""add item-level return requests and restocking

Revision ID: e4f5a6b7c8d9
Revises: e3f4a5b6c7d8
Create Date: 2026-11-04 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table(
        "return_requests", schema=None
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "completed_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "stock_restocked_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )

    op.create_table(
        "return_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("return_request_id", sa.Integer(), nullable=False),
        sa.Column("order_item_id", sa.Integer(), nullable=True),
        sa.Column("variant_id", sa.Integer(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "product_name", sa.String(length=160), nullable=False
        ),
        sa.Column("size", sa.String(length=20), nullable=False),
        sa.Column("color", sa.String(length=40), nullable=False),
        sa.Column("sku", sa.String(length=80), nullable=False),
        sa.Column(
            "restocked_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["return_request_id"],
            ["return_requests.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["order_item_id"],
            ["order_items.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["product_variants.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("return_items", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_return_items_return_request_id"),
            ["return_request_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_return_items_order_item_id"),
            ["order_item_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_return_items_variant_id"),
            ["variant_id"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("return_items", schema=None) as batch_op:
        batch_op.drop_index(
            batch_op.f("ix_return_items_variant_id")
        )
        batch_op.drop_index(
            batch_op.f("ix_return_items_order_item_id")
        )
        batch_op.drop_index(
            batch_op.f("ix_return_items_return_request_id")
        )

    op.drop_table("return_items")

    with op.batch_alter_table(
        "return_requests", schema=None
    ) as batch_op:
        batch_op.drop_column("stock_restocked_at")
        batch_op.drop_column("completed_at")
