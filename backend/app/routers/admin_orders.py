from datetime import date
from typing import Literal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Response,
    status as http_status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import Payment, Refund, User
from app.schemas.order import OrderOut, OrderStatusUpdate
from app.schemas.payment import (
    AdminPaymentOut,
    ManualReconciliationRequest,
    RefundCreate,
    RefundOut,
    RefundUpdate,
)
from app.schemas.return_request import (
    ReturnLinkRefundRequest,
    ReturnRequestOut,
    ReturnReviewRequest,
)
from app.services import admin_orders
from app.services import payments as payment_service
from app.services import refunds as refund_service
from app.services import returns as return_service
from app.services.email import (
    send_order_status_update,
    send_payment_confirmation,
    send_return_status_update,
)

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
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
):
    orders, total = admin_orders.list_orders(
        db,
        page=page,
        limit=limit,
        status_filter=status_filter,
        search=search,
        date_from=date_from,
        date_to=date_to,
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


@router.get(
    "/{order_id}/payments",
    response_model=list[AdminPaymentOut],
)
def get_order_payments(
    order_id: int,
    db: Session = Depends(get_db),
):
    order = admin_orders.get_order(db, order_id)

    if order is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return payment_service.list_order_payments(db, order.id)


@router.post(
    "/{order_id}/payments/{payment_id}/reconcile",
    response_model=AdminPaymentOut,
)
def reconcile_order_payment(
    order_id: int,
    payment_id: int,
    payload: ManualReconciliationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    order = admin_orders.get_order(db, order_id)

    if order is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    try:
        result = payment_service.reconcile_payment(
            db, current_user, order, payment_id, payload
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    if result.newly_paid:
        background_tasks.add_task(
            send_payment_confirmation,
            result.order.contact_email,
            result.order.id,
            result.order.contact_name,
            result.order.total,
            result.payment.reference,
        )

    return result.payment


@router.post(
    "/{order_id}/payments/{payment_id}/reconcile-provider",
    response_model=AdminPaymentOut,
)
def reconcile_order_payment_with_provider(
    order_id: int,
    payment_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    order = admin_orders.get_order(db, order_id)

    if order is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    try:
        result = payment_service.reconcile_with_provider(
            db, current_user, order, payment_id
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    if result.newly_paid:
        background_tasks.add_task(
            send_payment_confirmation,
            result.order.contact_email,
            result.order.id,
            result.order.contact_name,
            result.order.total,
            result.payment.reference,
        )

    return result.payment


@router.get(
    "/{order_id}/refunds",
    response_model=list[RefundOut],
)
def list_order_refunds(
    order_id: int,
    db: Session = Depends(get_db),
):
    order = admin_orders.get_order(db, order_id)

    if order is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return list(
        db.scalars(
            select(Refund)
            .where(Refund.order_id == order.id)
            .order_by(Refund.id.desc())
        ).all()
    )


@router.post(
    "/{order_id}/payments/{payment_id}/refunds",
    response_model=RefundOut,
    status_code=http_status.HTTP_201_CREATED,
)
def create_order_refund(
    order_id: int,
    payment_id: int,
    payload: RefundCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    order = admin_orders.get_order(db, order_id)

    if order is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    payment = db.scalar(
        select(Payment).where(
            Payment.id == payment_id,
            Payment.order_id == order.id,
        )
    )

    if payment is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Payment not found for this order.",
        )

    return refund_service.create_refund(
        db, current_user, order, payment, payload
    )


@router.patch(
    "/{order_id}/refunds/{refund_id}",
    response_model=RefundOut,
)
def update_order_refund(
    order_id: int,
    refund_id: int,
    payload: RefundUpdate,
    db: Session = Depends(get_db),
):
    order = admin_orders.get_order(db, order_id)

    if order is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    refund = db.scalar(
        select(Refund).where(
            Refund.id == refund_id,
            Refund.order_id == order.id,
        )
    )

    if refund is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Refund not found for this order.",
        )

    return refund_service.update_refund(db, order, refund, payload)


@router.get(
    "/{order_id}/returns",
    response_model=list[ReturnRequestOut],
)
def list_order_returns(
    order_id: int,
    db: Session = Depends(get_db),
):
    order = admin_orders.get_order(db, order_id)

    if order is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return return_service.list_returns(db, order.id)


@router.patch(
    "/{order_id}/returns/{return_id}",
    response_model=ReturnRequestOut,
)
def review_order_return(
    order_id: int,
    return_id: int,
    payload: ReturnReviewRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    order = admin_orders.get_order(db, order_id)

    if order is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    reviewed = return_service.review_return(
        db, current_user, order, return_id, payload
    )
    background_tasks.add_task(
        send_return_status_update,
        order.contact_email,
        order.id,
        reviewed.id,
        reviewed.status,
        payload.note,
    )
    return reviewed


@router.patch(
    "/{order_id}/returns/{return_id}/refund",
    response_model=ReturnRequestOut,
)
def link_return_refund(
    order_id: int,
    return_id: int,
    payload: ReturnLinkRefundRequest,
    db: Session = Depends(get_db),
):
    order = admin_orders.get_order(db, order_id)

    if order is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return return_service.link_refund(db, order, return_id, payload)


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    order = admin_orders.get_order(db, order_id)

    if order is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    try:
        updated = admin_orders.update_status(db, order, payload)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    background_tasks.add_task(
        send_order_status_update,
        updated.contact_email,
        updated.id,
        updated.status,
    )

    return updated
