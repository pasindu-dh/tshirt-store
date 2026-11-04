from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.schemas.return_request import AdminReturnQueueOut
from app.services import returns as return_service

router = APIRouter(
    prefix="/admin/returns",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)

ReturnStatusFilter = Literal[
    "requested", "approved", "rejected", "completed", "cancelled"
]


@router.get("", response_model=list[AdminReturnQueueOut])
def list_admin_returns(
    response: Response,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: ReturnStatusFilter | None = Query(
        None, alias="status"
    ),
    search: str | None = Query(None, max_length=100),
    db: Session = Depends(get_db),
):
    returns, total = return_service.list_admin_returns(
        db,
        page=page,
        limit=limit,
        status_filter=status_filter,
        search=search,
    )
    response.headers["X-Total-Count"] = str(total)
    return returns
