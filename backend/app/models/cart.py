from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common import utcnow

if TYPE_CHECKING:
    from app.models.product import ProductVariant


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "variant_id", name="uq_cart_user_variant"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"), index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    variant: Mapped["ProductVariant"] = relationship()
