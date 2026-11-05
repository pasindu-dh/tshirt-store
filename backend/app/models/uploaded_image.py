from datetime import datetime

from sqlalchemy import (
    DateTime,
    Integer,
    LargeBinary,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common import utcnow


class UploadedImage(Base):
    """Admin-uploaded product image stored in the database.

    Render Free has an ephemeral filesystem, so PostgreSQL is the source
    of truth for uploaded product images. The local uploads directory is
    kept only as a legacy/fallback cache for development.
    """

    __tablename__ = "uploaded_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(
        String(120), unique=True, index=True
    )
    content_type: Mapped[str] = mapped_column(String(80))
    size_bytes: Mapped[int] = mapped_column(Integer)
    data: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
