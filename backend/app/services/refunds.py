from datetime import date, datetime, time, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Order, Payment, Refund, User
from app.models.common import utcnow
from app.schemas.payment import (
    AdminRefundQueueOut,
    RefundCreate,
    RefundUpdate,
)
from app.services import payhere_api
from app.services.payment_events import record_event


def _committed_refunds_total(db: Session, payment_id: int) -> int:
    return int(
        db.scalar(
            select(func.coalesce(func.sum(Refund.amount), 0)).where(
                Refund.payment_id == payment_id,
                Refund.status.in_(
                    ("pending", "processing", "refunded")
                ),
            )
        )
        or 0
    )


def _completed_refunds_total(db: Session, payment_id: int) -> int:
    return int(
        db.scalar(
            select(func.coalesce(func.sum(Refund.amount), 0)).where(
                Refund.payment_id == payment_id,
                Refund.status == "refunded",
            )
        )
        or 0
    )


def _complete_refund(
    db: Session,
    order: Order,
    payment: Payment,
    refund: Refund,
) -> None:
    from fastapi import HTTPException, status

    if refund.status != "refunded" or refund.completed_at is not None:
        return

    refund.completed_at = utcnow()
    total = _completed_refunds_total(db, payment.id)
    full_refund = total >= payment.amount

    record_event(
        db,
        payment,
        status="refunded" if full_refund else "refund_partial",
        source="refund",
        note=(
            f"{refund.kind.title()} of LKR {refund.amount} completed "
            f"(total refunded LKR {total})."
        ),
    )

    if full_refund:
        if payment.status == "chargedback":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A chargedback payment cannot be converted to refunded.",
            )

        payment.status = "refunded"
        order.payment_status = "refunded"


def create_refund(
    db: Session,
    admin_user: User,
    order: Order,
    payment: Payment,
    payload: RefundCreate,
) -> Refund:
    from fastapi import HTTPException, status

    if payment.order_id != order.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found for this order.",
        )

    if payment.status != "paid":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Refunds can only be recorded against a paid payment.",
        )

    remaining = payment.amount - _committed_refunds_total(
        db, payment.id
    )

    if payload.amount > remaining:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Refund amount exceeds the remaining refundable "
                f"balance of LKR {remaining}."
            ),
        )

    provider = "manual"
    refund_status = "pending"

    if payload.process_with_provider:
        if not settings.payhere_api_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Provider refund API is not configured; record "
                    "the refund manually instead."
                ),
            )

        if not payment.provider_payment_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Verify the payment with PayHere before "
                    "requesting a provider refund."
                ),
            )

        provider = settings.normalized_payment_provider
        refund_status = "processing"

    refund = Refund(
        order_id=order.id,
        payment_id=payment.id,
        amount=payload.amount,
        kind=payload.kind,
        reason=payload.reason.strip(),
        notes=payload.notes.strip(),
        status=refund_status,
        provider=provider,
        requested_by_user_id=admin_user.id,
    )
    db.add(refund)
    db.commit()
    db.refresh(refund)

    if not payload.process_with_provider:
        return refund

    try:
        provider_refund = payhere_api.refund_payment(
            payment.provider_payment_id,
            amount=payload.amount,
            description=(
                f"FURZY {payload.kind} for order #{order.id}: "
                f"{payload.reason.strip()}"
            )[:200],
        )
    except payhere_api.PayHereApiError as exc:
        refund.status = "failed"
        refund.notes = (
            f"{refund.notes}\nProvider refund failed: {exc}".strip()
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    refund.provider_refund_id = provider_refund.refund_id
    refund.status = provider_refund.status

    if refund.status == "refunded":
        db.flush()
        _complete_refund(db, order, payment, refund)

    db.commit()
    db.refresh(refund)
    return refund


def update_refund(
    db: Session,
    order: Order,
    refund: Refund,
    payload: RefundUpdate,
) -> Refund:
    from fastapi import HTTPException, status

    if refund.order_id != order.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found for this order.",
        )

    if payload.status == refund.status:
        return refund

    if refund.status == "refunded":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Completed refunds are final.",
        )

    payment = db.get(Payment, refund.payment_id)

    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found for this refund.",
        )

    refund.status = payload.status

    if payload.provider_refund_id.strip():
        refund.provider_refund_id = payload.provider_refund_id.strip()

    if payload.note.strip():
        refund.notes = (
            f"{refund.notes}\n{payload.note.strip()}".strip()
        )

    if refund.status == "refunded":
        _complete_refund(db, order, payment, refund)

    db.commit()
    db.refresh(refund)
    return refund


def list_admin_refunds(
    db: Session,
    *,
    page: int,
    limit: int,
    status_filter: str | None = None,
    kind: str | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[list[AdminRefundQueueOut], int]:
    filters = []

    if status_filter:
        filters.append(Refund.status == status_filter)
    if kind:
        filters.append(Refund.kind == kind)
    if date_from is not None:
        filters.append(
            Refund.created_at
            >= datetime.combine(date_from, time.min)
        )
    if date_to is not None:
        filters.append(
            Refund.created_at
            < datetime.combine(
                date_to + timedelta(days=1), time.min
            )
        )

    if search and search.strip():
        term_value = search.strip()

        if term_value.isdigit():
            filters.append(
                or_(
                    Refund.id == int(term_value),
                    Refund.order_id == int(term_value),
                )
            )
        else:
            term = f"%{term_value}%"
            filters.append(
                or_(
                    Order.contact_name.ilike(term),
                    Order.contact_email.ilike(term),
                    Refund.reason.ilike(term),
                    Refund.provider_refund_id.ilike(term),
                    Payment.reference.ilike(term),
                )
            )

    joined = (
        select(Refund, Order, Payment)
        .join(Order, Refund.order_id == Order.id)
        .join(Payment, Refund.payment_id == Payment.id)
    )
    total = int(
        db.scalar(
            select(func.count(Refund.id))
            .join(Order, Refund.order_id == Order.id)
            .join(Payment, Refund.payment_id == Payment.id)
            .where(*filters)
        )
        or 0
    )
    rows = db.execute(
        joined.where(*filters)
        .order_by(
            Refund.created_at.desc(), Refund.id.desc()
        )
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    items = [
        AdminRefundQueueOut(
            id=refund.id,
            order_id=refund.order_id,
            payment_id=refund.payment_id,
            amount=refund.amount,
            kind=refund.kind,
            status=refund.status,
            provider=refund.provider,
            provider_refund_id=refund.provider_refund_id,
            reason=refund.reason,
            notes=refund.notes,
            created_at=refund.created_at,
            completed_at=refund.completed_at,
            order_contact_name=order.contact_name,
            order_contact_email=order.contact_email,
            order_total=order.total,
            order_status=order.status,
            order_payment_status=order.payment_status,
            payment_reference=payment.reference,
        )
        for refund, order, payment in rows
    ]

    return items, total
