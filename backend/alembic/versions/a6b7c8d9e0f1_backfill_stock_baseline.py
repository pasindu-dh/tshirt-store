"""backfill stock movement baseline

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-11-04 13:25:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "a6b7c8d9e0f1"
down_revision: Union[str, Sequence[str], None] = "f5a6b7c8d9e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BASELINE_REASON = (
    "Starting balance recorded during inventory audit rollout."
)


def upgrade() -> None:
    """Record the current stock as an opening audit balance."""
    op.execute(
        f"""
        INSERT INTO stock_movements (
            variant_id,
            product_id,
            movement_type,
            quantity_delta,
            stock_before,
            stock_after,
            product_name,
            size,
            color,
            sku,
            reason,
            created_at
        )
        SELECT
            pv.id,
            pv.product_id,
            'initial_stock',
            pv.stock,
            0,
            pv.stock,
            p.name,
            pv.size,
            pv.color,
            pv.sku,
            '{BASELINE_REASON}',
            CURRENT_TIMESTAMP
        FROM product_variants AS pv
        JOIN products AS p ON p.id = pv.product_id
        WHERE pv.stock > 0
        """
    )


def downgrade() -> None:
    """Remove the opening balance rows."""
    op.execute(
        "DELETE FROM stock_movements "
        "WHERE movement_type = 'initial_stock' "
        f"AND reason = '{BASELINE_REASON}'"
    )
