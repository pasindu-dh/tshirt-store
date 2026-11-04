from datetime import date
from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.schemas.reporting import FinancialReportOut
from app.services import reporting

router = APIRouter(
    prefix="/admin/reports",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("/financial", response_model=FinancialReportOut)
def get_financial_report(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    group_by: Literal["day", "month"] = Query("month"),
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

    return reporting.financial_report(
        db,
        date_from=date_from,
        date_to=date_to,
        group_by=group_by,
    )
