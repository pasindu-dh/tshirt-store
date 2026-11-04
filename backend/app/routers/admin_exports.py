from datetime import date, datetime, timezone
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
from app.schemas.inventory import StockMovementType
from app.services import exports

router = APIRouter(
    prefix="/admin/exports",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)

OrderStatusFilter = Literal[
    "pending",
    "confirmed",
    "shipped",
    "delivered",
    "cancelled",
]
ReturnStatusFilter = Literal[
    "requested", "approved", "rejected", "completed", "cancelled"
]
RefundStatusFilter = Literal[
    "pending", "processing", "refunded", "failed"
]
RefundKindFilter = Literal["refund", "return"]


def _validate_date_range(
    date_from: date | None, date_to: date | None
) -> None:
    if (
        date_from is not None
        and date_to is not None
        and date_from > date_to
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be on or before date_to.",
        )


def _csv_response(
    name: str,
    headers: list[str],
    rows: list[list],
) -> Response:
    filename = (
        f"furzy-{name}-"
        f"{datetime.now(timezone.utc).date().isoformat()}.csv"
    )
    return Response(
        content=exports.to_csv(headers, rows),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            ),
            "Cache-Control": "no-store",
        },
    )


@router.get("/products.csv")
def export_products(db: Session = Depends(get_db)):
    headers, rows = exports.catalog_rows(db)
    return _csv_response("products", headers, rows)


@router.get("/orders.csv")
def export_orders(
    status_filter: OrderStatusFilter | None = Query(
        None, alias="status"
    ),
    search: str | None = Query(None, max_length=100),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
):
    _validate_date_range(date_from, date_to)
    headers, rows = exports.order_rows(
        db,
        status_filter=status_filter,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
    return _csv_response("orders", headers, rows)


@router.get("/customers.csv")
def export_customers(
    search: str | None = Query(None, max_length=100),
    db: Session = Depends(get_db),
):
    headers, rows = exports.customer_rows(
        db, search=search
    )
    return _csv_response("customers", headers, rows)


@router.get("/returns.csv")
def export_returns(
    status_filter: ReturnStatusFilter | None = Query(
        None, alias="status"
    ),
    search: str | None = Query(None, max_length=100),
    db: Session = Depends(get_db),
):
    headers, rows = exports.return_rows(
        db,
        status_filter=status_filter,
        search=search,
    )
    return _csv_response("returns", headers, rows)


@router.get("/refunds.csv")
def export_refunds(
    status_filter: RefundStatusFilter | None = Query(
        None, alias="status"
    ),
    kind: RefundKindFilter | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
):
    _validate_date_range(date_from, date_to)
    headers, rows = exports.refund_rows(
        db,
        status_filter=status_filter,
        kind=kind,
        date_from=date_from,
        date_to=date_to,
    )
    return _csv_response("refunds", headers, rows)


@router.get("/stock-movements.csv")
def export_stock_movements(
    movement_type: StockMovementType | None = Query(None),
    variant_id: int | None = Query(None, ge=1),
    product_id: int | None = Query(None, ge=1),
    order_id: int | None = Query(None, ge=1),
    search: str | None = Query(None, max_length=100),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
):
    _validate_date_range(date_from, date_to)
    headers, rows = exports.stock_movement_rows(
        db,
        movement_type=movement_type,
        variant_id=variant_id,
        product_id=product_id,
        order_id=order_id,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
    return _csv_response(
        "stock-movements", headers, rows
    )


@router.get("/financial.csv")
def export_financial(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    group_by: Literal["day", "month"] = Query("month"),
    db: Session = Depends(get_db),
):
    _validate_date_range(date_from, date_to)
    headers, rows = exports.financial_rows(
        db,
        date_from=date_from,
        date_to=date_to,
        group_by=group_by,
    )
    return _csv_response("financial", headers, rows)
