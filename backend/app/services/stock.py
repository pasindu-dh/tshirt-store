from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Coupon, Order, Payment, ProductVariant
from app.models.common import utcnow
from app.services.payment_events import record_event


def release_order_stock(
    db: Session, order: Order, *, reason: str
) -> bool:
    """Release an order's reserved stock and coupon usage exactly once."""

    locked_order = db.scalar(
        select(Order)
        .where(Order.id == order.id)
        .with_for_update()
    )

    if locked_order is None or locked_order.stock_released_at is not None:
        return False

    order = locked_order
    variant_ids = [
        item.variant_id
        for item in order.items
        if item.variant_id is not None
    ]

    if variant_ids:
        variants = db.scalars(
            select(ProductVariant)
            .where(ProductVariant.id.in_(variant_ids))
            .order_by(ProductVariant.id)
            .with_for_update()
        ).all()
        variants_by_id = {
            variant.id: variant for variant in variants
        }

        for item in order.items:
            variant = (
                variants_by_id.get(item.variant_id)
                if item.variant_id is not None
                else None
            )

            if variant is not None:
                variant.stock += item.quantity

    if order.discount_code:
        coupon = db.scalar(
            select(Coupon)
            .where(Coupon.code == order.discount_code)
            .with_for_update()
        )

        if coupon is not None and coupon.used_count > 0:
            coupon.used_count -= 1

    order.stock_released_at = utcnow()
    order.stock_release_reason = reason
    return True


def expire_unpaid_online_orders(
    db: Session, *, now: datetime | None = None
) -> int:
    """Cancel expired unpaid online orders and release their stock once."""

    cutoff = now or utcnow()
    orders = db.scalars(
        select(Order)
        .where(
            Order.payment_method == "online",
            Order.reservation_expires_at.is_not(None),
            Order.reservation_expires_at <= cutoff,
            Order.stock_released_at.is_(None),
            Order.status.in_(("pending", "confirmed")),
            Order.payment_status.notin_(("paid", "chargedback")),
        )
        .order_by(Order.id)
        .options(selectinload(Order.items))
        .with_for_update()
    ).all()
    released_count = 0

    for order in orders:
        # Re-check after acquiring the row lock.
        if (
            order.stock_released_at is not None
            or order.payment_status in {"paid", "chargedback"}
            or order.status not in {"pending", "confirmed"}
        ):
            continue

        if not release_order_stock(
            db, order, reason="expired"
        ):
            continue

        order.status = "cancelled"
        order.payment_status = "cancelled"
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
                status_code="expired",
                source="system",
                note="Stock reservation expired.",
            )

        released_count += 1

    db.commit()
    return released_count
