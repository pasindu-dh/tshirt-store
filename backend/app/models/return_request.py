from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common import utcnow
from app.models.payment import Refund


class ReturnRequest(Base):
    __tablename__ = "return_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default="requested", index=True
    )
    reason: Mapped[str] = mapped_column(String(500))
    notes: Mapped[str] = mapped_column(
        Text, default="", server_default=""
    )
    refund_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("refunds.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    review_note: Mapped[str] = mapped_column(
        Text, default="", server_default=""
    )
    reviewed_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    refund: Mapped[Optional[Refund]] = relationship()
