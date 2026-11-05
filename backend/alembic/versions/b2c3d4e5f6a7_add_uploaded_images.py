"""add database-backed uploaded images

Revision ID: b2c3d4e5f6a7
Revises: a3b4c5d6e7f8
Create Date: 2026-11-05 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "uploaded_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "filename", sa.String(length=120), nullable=False
        ),
        sa.Column(
            "content_type", sa.String(length=80), nullable=False
        ),
        sa.Column(
            "size_bytes", sa.Integer(), nullable=False
        ),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_uploaded_images_filename",
        "uploaded_images",
        ["filename"],
        unique=True,
    )
    op.create_index(
        "ix_uploaded_images_created_at",
        "uploaded_images",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_uploaded_images_created_at",
        table_name="uploaded_images",
    )
    op.drop_index(
        "ix_uploaded_images_filename",
        table_name="uploaded_images",
    )
    op.drop_table("uploaded_images")
