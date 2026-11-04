from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def liveness():
    return {"status": "ok"}


@router.get("/ready")
def readiness(
    response: Response,
    db: Session = Depends(get_db),
):
    checks = {}

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    probe_path = None

    try:
        uploads = Path(settings.uploads_dir)
        uploads.mkdir(parents=True, exist_ok=True)
        probe_path = uploads / f".readiness-{uuid4().hex}"
        probe_path.write_text("ok", encoding="utf-8")
        probe_path.unlink()
        checks["uploads"] = "ok"
    except Exception:
        checks["uploads"] = "error"

    if probe_path is not None and probe_path.exists():
        try:
            probe_path.unlink()
        except OSError:
            pass

    ready = all(
        value == "ok" for value in checks.values()
    )

    if not ready:
        response.status_code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
        )

    return {
        "status": "ready" if ready else "unready",
        "checks": checks,
    }
