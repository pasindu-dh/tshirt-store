from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common import utcnow


class ShippingMethod(Base):
    __tablename__ = "shipping_methods"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(80), unique=True, index=True
    )
    description: Mapped[str] = mapped_column(
        String(500), default="", server_default=""
    )
    fee_lkr: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
