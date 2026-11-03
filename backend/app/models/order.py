from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common import utcnow


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default="pending", index=True
    )
    payment_method: Mapped[str] = mapped_column(String(20), default="cod")
    payment_status: Mapped[str] = mapped_column(
        String(30), default="pending"
    )
    subtotal: Mapped[int] = mapped_column(Integer)
    shipping_fee: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer)

    contact_name: Mapped[str] = mapped_column(String(120))
    contact_email: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(30))
    address_line1: Mapped[str] = mapped_column(String(200))
    address_line2: Mapped[str] = mapped_column(String(200), default="")
    city: Mapped[str] = mapped_column(String(100))
    postal_code: Mapped[str] = mapped_column(String(20), default="")
    country: Mapped[str] = mapped_column(String(100), default="Sri Lanka")
    notes: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderItem.id",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    variant_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    product_name: Mapped[str] = mapped_column(String(160))
    product_slug: Mapped[str] = mapped_column(String(180))
    image: Mapped[str] = mapped_column(String(500), default="")
    size: Mapped[str] = mapped_column(String(20))
    color: Mapped[str] = mapped_column(String(40))
    sku: Mapped[str] = mapped_column(String(80))
    unit_price: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer)
    line_total: Mapped[int] = mapped_column(Integer)

    order: Mapped["Order"] = relationship(back_populates="items")
