"""add inventory thresholds and stock movements

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-11-04 13:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f5a6b7c8d9e0"
down_revision: Union[str, Sequence[str], None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table(
        "product_variants", schema=None
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "low_stock_threshold",
                sa.Integer(),
                nullable=False,
                server_default="5",
            )
        )

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("return_request_id", sa.Integer(), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "movement_type", sa.String(length=30), nullable=False
        ),
        sa.Column("quantity_delta", sa.Integer(), nullable=False),
        sa.Column("stock_before", sa.Integer(), nullable=False),
        sa.Column("stock_after", sa.Integer(), nullable=False),
        sa.Column(
            "product_name", sa.String(length=160), nullable=False
        ),
        sa.Column("size", sa.String(length=20), nullable=False),
        sa.Column("color", sa.String(length=40), nullable=False),
        sa.Column("sku", sa.String(length=80), nullable=False),
        sa.Column(
            "reason",
            sa.String(length=300),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["product_variants.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["return_request_id"],
            ["return_requests.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table(
        "stock_movements", schema=None
    ) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_stock_movements_variant_id"),
            ["variant_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_stock_movements_product_id"),
            ["product_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_stock_movements_order_id"),
            ["order_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_stock_movements_return_request_id"),
            ["return_request_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_stock_movements_movement_type"),
            ["movement_type"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_stock_movements_created_at"),
            ["created_at"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table(
        "stock_movements", schema=None
    ) as batch_op:
        batch_op.drop_index(
            batch_op.f("ix_stock_movements_created_at")
        )
        batch_op.drop_index(
            batch_op.f("ix_stock_movements_movement_type")
        )
        batch_op.drop_index(
            batch_op.f("ix_stock_movements_return_request_id")
        )
        batch_op.drop_index(batch_op.f("ix_stock_movements_order_id"))
        batch_op.drop_index(
            batch_op.f("ix_stock_movements_product_id")
        )
        batch_op.drop_index(
            batch_op.f("ix_stock_movements_variant_id")
        )

    op.drop_table("stock_movements")

    with op.batch_alter_table(
        "product_variants", schema=None
    ) as batch_op:
        batch_op.drop_column("low_stock_threshold")
