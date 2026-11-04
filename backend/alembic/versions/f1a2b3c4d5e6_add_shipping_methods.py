"""add configurable shipping methods

Revision ID: f1a2b3c4d5e6
Revises: e0f1a2b3c4d5
Create Date: 2026-11-04 17:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e0f1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "shipping_methods",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "name", sa.String(length=80), nullable=False
        ),
        sa.Column(
            "description",
            sa.String(length=500),
            nullable=False,
            server_default="",
        ),
        sa.Column("fee_lkr", sa.Integer(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    with op.batch_alter_table(
        "shipping_methods", schema=None
    ) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_shipping_methods_name"),
            ["name"],
            unique=True,
        )

    op.execute(
        "INSERT INTO shipping_methods "
        "(name, description, fee_lkr, is_active, sort_order, "
        "created_at, updated_at) VALUES "
        "('Standard Delivery', "
        "'Standard delivery within Sri Lanka.', 350, true, 0, "
        "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
    )

    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "shipping_method_id",
                sa.Integer(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "shipping_method_name",
                sa.String(length=120),
                nullable=False,
                server_default="",
            )
        )
        batch_op.create_index(
            batch_op.f("ix_orders_shipping_method_id"),
            ["shipping_method_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "fk_orders_shipping_method_id",
            "shipping_methods",
            ["shipping_method_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.execute(
        "UPDATE orders "
        "SET shipping_method_name = 'Standard Delivery' "
        "WHERE shipping_fee > 0 "
        "AND shipping_method_name = ''"
    )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_orders_shipping_method_id",
            type_="foreignkey",
        )
        batch_op.drop_index(
            batch_op.f("ix_orders_shipping_method_id")
        )
        batch_op.drop_column("shipping_method_name")
        batch_op.drop_column("shipping_method_id")

    with op.batch_alter_table(
        "shipping_methods", schema=None
    ) as batch_op:
        batch_op.drop_index(
            batch_op.f("ix_shipping_methods_name")
        )

    op.drop_table("shipping_methods")
