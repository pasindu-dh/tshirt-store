from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status as http_status,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.schemas.order import OrderOut, OrderStatusUpdate
from app.services import admin_orders

OrderStatusFilter = Literal[
    "pending",
    "confirmed",
    "shipped",
    "delivered",
    "cancelled",
]

router = APIRouter(
    prefix="/admin/orders",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=list[OrderOut])
def list_orders(
    response: Response,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: OrderStatusFilter | None = Query(
        None, alias="status"
    ),
    search: str | None = Query(None, max_length=100),
    db: Session = Depends(get_db),
):
    orders, total = admin_orders.list_orders(
        db,
        page=page,
        limit=limit,
        status_filter=status_filter,
        search=search,
    )
    response.headers["X-Total-Count"] = str(total)
    return orders


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = admin_orders.get_order(db, order_id)

    if order is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return order


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
):
    order = admin_orders.get_order(db, order_id)

    if order is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    try:
        return admin_orders.update_status(db, order, payload)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
