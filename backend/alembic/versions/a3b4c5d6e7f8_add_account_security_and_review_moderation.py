"""add account security and review moderation

Revision ID: a3b4c5d6e7f8
Revises: f1a2b3c4d5e6
Create Date: 2026-11-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "email_verified_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "token_version",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )

    # Accounts created before email verification existed are treated as
    # verified so enabling verification later does not lock them out.
    op.execute(
        "UPDATE users SET email_verified_at = created_at "
        "WHERE email_verified_at IS NULL"
    )

    with op.batch_alter_table("reviews", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default="published",
            )
        )
        batch_op.create_index(
            batch_op.f("ix_reviews_status"),
            ["status"],
            unique=False,
        )

    op.create_table(
        "auth_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "purpose", sa.String(length=30), nullable=False
        ),
        sa.Column(
            "token_hash", sa.String(length=64), nullable=False
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "used_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_auth_tokens_user_id",
        "auth_tokens",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_auth_tokens_purpose",
        "auth_tokens",
        ["purpose"],
        unique=False,
    )
    op.create_index(
        "ix_auth_tokens_token_hash",
        "auth_tokens",
        ["token_hash"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_auth_tokens_token_hash",
        table_name="auth_tokens",
    )
    op.drop_index(
        "ix_auth_tokens_purpose",
        table_name="auth_tokens",
    )
    op.drop_index(
        "ix_auth_tokens_user_id",
        table_name="auth_tokens",
    )
    op.drop_table("auth_tokens")

    with op.batch_alter_table("reviews", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_reviews_status"))
        batch_op.drop_column("status")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("token_version")
        batch_op.drop_column("email_verified_at")
