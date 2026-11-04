from datetime import date
from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.schemas.payment import AdminRefundQueueOut
from app.services import refunds as refund_service

router = APIRouter(
    prefix="/admin/refunds",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)

RefundStatusFilter = Literal[
    "pending", "processing", "refunded", "failed"
]
RefundKindFilter = Literal["refund", "return"]


@router.get("", response_model=list[AdminRefundQueueOut])
def list_refunds(
    response: Response,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: RefundStatusFilter | None = Query(
        None, alias="status"
    ),
    kind: RefundKindFilter | None = Query(None),
    search: str | None = Query(None, max_length=100),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
):
    if (
        date_from is not None
        and date_to is not None
        and date_from > date_to
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be on or before date_to.",
        )

    refunds, total = refund_service.list_admin_refunds(
        db,
        page=page,
        limit=limit,
        status_filter=status_filter,
        kind=kind,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
    response.headers["X-Total-Count"] = str(total)
    return refunds
