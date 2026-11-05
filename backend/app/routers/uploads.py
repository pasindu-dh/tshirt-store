import logging
import mimetypes
import re
import uuid
from io import BytesIO
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.exc import (
    OperationalError,
    ProgrammingError,
    SQLAlchemyError,
)
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import require_admin
from app.models import UploadedImage
from app.schemas.upload import ImageUploadOut

logger = logging.getLogger("furzy.uploads")

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}
FORMAT_EXTENSIONS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
}
FORMAT_CONTENT_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}
MAX_IMAGE_PIXELS = 40_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

SAFE_FILENAME = re.compile(
    r"^[A-Za-z0-9_-]{1,100}\.(?:jpg|jpeg|png|webp)$",
    re.IGNORECASE,
)
MISSING_TABLE_MARKERS = (
    "no such table",
    "does not exist",
    "undefinedtable",
)
CACHE_HEADERS = {
    "Cache-Control": "public, max-age=31536000, immutable"
}

router = APIRouter(
    prefix="/admin/uploads",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)
files_router = APIRouter(tags=["uploads"])


def _is_missing_table(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(
        marker in message for marker in MISSING_TABLE_MARKERS
    )


def _write_fallback(filename: str, contents: bytes) -> None:
    uploads_dir = Path(settings.uploads_dir)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    (uploads_dir / filename).write_bytes(contents)


@router.post(
    "",
    response_model=ImageUploadOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if (file.content_type or "") not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG, PNG, and WebP images are allowed.",
        )

    max_megabytes = settings.max_upload_bytes // (1024 * 1024)

    if file.size is not None and file.size > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Image must be {max_megabytes} MB or smaller.",
        )

    contents = await file.read()

    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Image must be {max_megabytes} MB or smaller.",
        )

    try:
        with Image.open(BytesIO(contents)) as image:
            image_format = image.format
            image.verify()
    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        Image.DecompressionBombError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid image.",
        ) from exc

    extension = FORMAT_EXTENSIONS.get(image_format or "")
    content_type = FORMAT_CONTENT_TYPES.get(image_format or "")

    if extension is None or content_type is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG, PNG, and WebP images are allowed.",
        )

    filename = f"{uuid.uuid4().hex}{extension}"
    db.add(
        UploadedImage(
            filename=filename,
            content_type=content_type,
            size_bytes=len(contents),
            data=contents,
        )
    )

    try:
        db.commit()
    except (ProgrammingError, OperationalError) as exc:
        db.rollback()

        if _is_missing_table(exc):
            if settings.is_production:
                # Never silently store production uploads on an
                # ephemeral filesystem; require the migration.
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=(
                        "Image storage is not initialized. Run database "
                        "migrations and try again."
                    ),
                ) from exc

            # Preserve local development behavior until the new
            # migration is applied.
            logger.warning(
                "uploaded_images table is missing; using the local "
                "uploads directory. Run `alembic upgrade head`."
            )

            try:
                _write_fallback(filename, contents)
            except OSError as write_error:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Image storage is temporarily unavailable.",
                ) from write_error
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Image storage is temporarily unavailable.",
            ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Image storage is temporarily unavailable.",
        ) from exc

    return ImageUploadOut(url=f"/uploads/{filename}")


@files_router.get("/uploads/{filename}")
def serve_uploaded_image(
    filename: str,
    db: Session = Depends(get_db),
):
    if not SAFE_FILENAME.fullmatch(filename):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found.",
        )

    image = None

    try:
        image = db.scalar(
            select(UploadedImage).where(
                UploadedImage.filename == filename
            )
        )
    except (ProgrammingError, OperationalError):
        db.rollback()
    except SQLAlchemyError:
        db.rollback()

    if image is not None:
        return Response(
            content=bytes(image.data),
            media_type=image.content_type,
            headers=CACHE_HEADERS,
        )

    # Legacy/local fallback. On Render Free this directory is ephemeral;
    # the database is the durable source of truth.
    path = Path(settings.uploads_dir) / filename

    try:
        if path.is_file():
            media_type = (
                mimetypes.guess_type(filename)[0]
                or "application/octet-stream"
            )
            return FileResponse(
                path,
                media_type=media_type,
                headers=CACHE_HEADERS,
            )
    except OSError:
        pass

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Image not found.",
    )
