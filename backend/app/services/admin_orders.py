from datetime import date, datetime, time, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Category,
    Order,
    Payment,
    Product,
    ProductVariant,
    Refund,
    ReturnRequest,
)
from app.schemas.order import AdminOrderStatsOut, OrderStatusUpdate
from app.services.payment_events import record_event
from app.services.reporting import (
    PENDING_REFUND_STATUSES,
    REVENUE_PAYMENT_STATUSES,
)
from app.services.stock import release_order_stock

ALLOWED_TRANSITIONS = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"shipped", "cancelled"},
    "shipped": {"delivered"},
    "delivered": set(),
    "cancelled": set(),
}


def list_orders(
    db: Session,
    *,
    page: int,
    limit: int,
    status_filter: str | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[list[Order], int]:
    filters = []

    if status_filter:
        filters.append(Order.status == status_filter)

    if date_from is not None:
        filters.append(
            Order.created_at >= datetime.combine(date_from, time.min)
        )

    if date_to is not None:
        filters.append(
            Order.created_at
            < datetime.combine(
                date_to + timedelta(days=1), time.min
            )
        )

    if search and search.strip():
        term_value = search.strip()

        if term_value.isdigit():
            filters.append(Order.id == int(term_value))
        else:
            term = f"%{term_value}%"
            filters.append(
                or_(
                    Order.contact_name.ilike(term),
                    Order.contact_email.ilike(term),
                    Order.phone.ilike(term),
                )
            )

    total = db.scalar(
        select(func.count(Order.id)).where(*filters)
    ) or 0

    orders = list(
        db.scalars(
            select(Order)
            .where(*filters)
            .options(selectinload(Order.items))
            .order_by(Order.created_at.desc(), Order.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )

    return orders, total


def get_order(db: Session, order_id: int) -> Order | None:
    return db.scalar(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items))
    )


def update_status(
    db: Session,
    order: Order,
    payload: OrderStatusUpdate,
    *,
    actor_user_id: int | None = None,
) -> Order:
    new_status = payload.status
    current_status = order.status

    if new_status == current_status:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Order is already {current_status}",
        )

    if new_status not in ALLOWED_TRANSITIONS.get(current_status, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot change order status from "
                f"{current_status} to {new_status}"
            ),
        )

    if new_status == "cancelled":
        release_order_stock(
            db,
            order,
            reason="cancelled",
            actor_user_id=actor_user_id,
        )

        if order.payment_status not in {"paid", "chargedback"}:
            order.payment_status = "cancelled"

        if order.payment_method == "online":
            pending_payments = db.scalars(
                select(Payment)
                .where(
                    Payment.order_id == order.id,
                    Payment.status.in_(("pending", "failed")),
                )
                .with_for_update()
            ).all()

            for payment in pending_payments:
                payment.status = "cancelled"
                record_event(
                    db,
                    payment,
                    status="cancelled",
                    status_code="cancelled",
                    source="system",
                    note="Order cancelled by admin.",
                )
    elif new_status == "delivered":
        if (
            order.payment_method == "online"
            and order.payment_status != "paid"
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Online payment must be paid before delivery."
                ),
            )

        if order.payment_method == "cod":
            order.payment_status = "paid"

    order.status = new_status

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    updated = get_order(db, order.id)

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Order could not be loaded after update",
        )

    return updated


def get_stats(db: Session) -> AdminOrderStatsOut:
    status_counts = dict(
        db.execute(
            select(Order.status, func.count(Order.id)).group_by(
                Order.status
            )
        ).all()
    )
    orders_total = sum(status_counts.values())
    open_orders = sum(
        status_counts.get(item, 0)
        for item in ("pending", "confirmed", "shipped")
    )
    revenue_scope = (
        Order.status == "delivered",
        Order.payment_status.in_(REVENUE_PAYMENT_STATUSES),
    )
    gross_revenue = int(
        db.scalar(
            select(func.coalesce(func.sum(Order.total), 0)).where(
                *revenue_scope
            )
        )
        or 0
    )
    refunded_total = int(
        db.scalar(
            select(func.coalesce(func.sum(Refund.amount), 0))
            .join(Order, Refund.order_id == Order.id)
            .where(*revenue_scope, Refund.status == "refunded")
        )
        or 0
    )
    pending_refund_total = int(
        db.scalar(
            select(func.coalesce(func.sum(Refund.amount), 0))
            .join(Order, Refund.order_id == Order.id)
            .where(
                *revenue_scope,
                Refund.status.in_(PENDING_REFUND_STATUSES),
            )
        )
        or 0
    )
    refund_count = int(
        db.scalar(
            select(func.count(Refund.id))
            .join(Order, Refund.order_id == Order.id)
            .where(*revenue_scope)
        )
        or 0
    )
    returns_total = int(
        db.scalar(select(func.count(ReturnRequest.id))) or 0
    )
    open_returns = int(
        db.scalar(
            select(func.count(ReturnRequest.id)).where(
                ReturnRequest.status.in_(("requested", "approved"))
            )
        )
        or 0
    )
    revenue = gross_revenue - refunded_total
    products_total = db.scalar(select(func.count(Product.id))) or 0
    products_active = db.scalar(
        select(func.count(Product.id)).where(Product.is_active.is_(True))
    ) or 0
    categories_total = db.scalar(select(func.count(Category.id))) or 0
    low_stock_variants = db.scalar(
        select(func.count(ProductVariant.id))
        .join(Product, ProductVariant.product_id == Product.id)
        .where(
            ProductVariant.stock
            <= ProductVariant.low_stock_threshold,
            Product.is_active.is_(True),
        )
    ) or 0
    out_of_stock_variants = db.scalar(
        select(func.count(ProductVariant.id))
        .join(Product, ProductVariant.product_id == Product.id)
        .where(
            ProductVariant.stock <= 0,
            Product.is_active.is_(True),
        )
    ) or 0

    return AdminOrderStatsOut(
        products_total=products_total,
        products_active=products_active,
        categories_total=categories_total,
        low_stock_variants=low_stock_variants,
        out_of_stock_variants=out_of_stock_variants,
        orders_total=orders_total,
        pending_orders=status_counts.get("pending", 0),
        confirmed_orders=status_counts.get("confirmed", 0),
        shipped_orders=status_counts.get("shipped", 0),
        delivered_orders=status_counts.get("delivered", 0),
        cancelled_orders=status_counts.get("cancelled", 0),
        open_orders=open_orders,
        revenue=revenue,
        gross_revenue=gross_revenue,
        refunded_total=refunded_total,
        pending_refund_total=pending_refund_total,
        refund_count=refund_count,
        open_returns=open_returns,
        returns_total=returns_total,
    )
