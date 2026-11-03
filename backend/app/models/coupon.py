from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common import utcnow


class Coupon(Base):
    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(
        String(40), unique=True, index=True
    )
    description: Mapped[str] = mapped_column(String(200), default="")
    discount_type: Mapped[str] = mapped_column(
        String(20), default="percent"
    )
    value: Mapped[int] = mapped_column(Integer)
    min_subtotal: Mapped[int] = mapped_column(Integer, default=0)
    usage_limit: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    starts_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
