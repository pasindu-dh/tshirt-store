"""add reviews, wishlist, coupons, and order discounts

Revision ID: b7d9e1f2a3c4
Revises: fe8442a53879
Create Date: 2026-11-04 00:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7d9e1f2a3c4"
down_revision: Union[str, Sequence[str], None] = "fe8442a53879"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_id", "user_id", name="uq_review_product_user"
        ),
    )
    with op.batch_alter_table("reviews", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_reviews_product_id"),
            ["product_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_reviews_user_id"),
            ["user_id"],
            unique=False,
        )

    op.create_table(
        "wishlist_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "product_id",
            name="uq_wishlist_user_product",
        ),
    )
    with op.batch_alter_table("wishlist_items", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_wishlist_items_user_id"),
            ["user_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_wishlist_items_product_id"),
            ["product_id"],
            unique=False,
        )

    op.create_table(
        "coupons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column(
            "description", sa.String(length=200), nullable=False
        ),
        sa.Column(
            "discount_type", sa.String(length=20), nullable=False
        ),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("min_subtotal", sa.Integer(), nullable=False),
        sa.Column("usage_limit", sa.Integer(), nullable=True),
        sa.Column("used_count", sa.Integer(), nullable=False),
        sa.Column(
            "starts_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "expires_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("coupons", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_coupons_code"),
            ["code"],
            unique=True,
        )

    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "discount_code",
                sa.String(length=40),
                server_default=sa.text("''"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "discount_amount",
                sa.Integer(),
                server_default=sa.text("0"),
                nullable=False,
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.drop_column("discount_amount")
        batch_op.drop_column("discount_code")

    with op.batch_alter_table("coupons", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_coupons_code"))

    op.drop_table("coupons")

    with op.batch_alter_table("wishlist_items", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_wishlist_items_product_id"))
        batch_op.drop_index(batch_op.f("ix_wishlist_items_user_id"))

    op.drop_table("wishlist_items")

    with op.batch_alter_table("reviews", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_reviews_user_id"))
        batch_op.drop_index(batch_op.f("ix_reviews_product_id"))

    op.drop_table("reviews")
