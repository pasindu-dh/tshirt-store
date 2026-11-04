import hashlib
import hmac
import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.models import Order, Payment, User
from app.models.common import utcnow
from app.schemas.payment import (
    ManualReconciliationRequest,
    PaymentConfigOut,
    PaymentSessionOut,
    PaymentStatusOut,
)
from app.services.payment_events import record_event

logger = logging.getLogger("furzy.payments")

PAYHERE_SANDBOX_URL = "https://sandbox.payhere.lk/pay/checkout"
PAYHERE_LIVE_URL = "https://www.payhere.lk/pay/checkout"

PAYHERE_STATUS_MAP = {
    "2": "paid",
    "0": "pending",
    "-1": "cancelled",
    "-2": "failed",
    "-3": "chargedback",
}


@dataclass
class PaymentCompletionResult:
    order_id: int
    reference: str
    status: str
    newly_paid: bool
    contact_email: str
    contact_name: str
    total: int


@dataclass
class PaymentNotificationResult:
    response_status: str
    newly_paid: bool = False
    order_id: int | None = None
    contact_email: str = ""
    contact_name: str = ""
    total: int = 0
    reference: str = ""


@dataclass
class ReconciliationResult:
    payment: Payment
    newly_paid: bool
    order: Order


def _md5_upper(value: str) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest().upper()


def _payhere_secret_hash() -> str:
    return _md5_upper(settings.payhere_merchant_secret)


def _payhere_signature(
    merchant_id: str,
    order_id: str,
    amount: str,
    currency: str,
    secret_hash: str,
) -> str:
    return _md5_upper(
        f"{merchant_id}{order_id}{amount}{currency}{secret_hash}"
    )


def _payhere_notification_signature(
    merchant_id: str,
    order_id: str,
    amount: str,
    currency: str,
    status_code: str,
    secret_hash: str,
) -> str:
    return _md5_upper(
        f"{merchant_id}{order_id}{amount}{currency}"
        f"{status_code}{secret_hash}"
    )


def get_config() -> PaymentConfigOut:
    provider = settings.normalized_payment_provider

    return PaymentConfigOut(
        provider=provider,
        online_enabled=settings.online_payments_enabled,
        currency=settings.payment_currency.strip().upper(),
        mock_enabled=(
            provider == "mock"
            and settings.payment_mock_enabled
            and not settings.is_production
        ),
    )


def _require_order(
    db: Session, user: User, order_id: int
) -> Order:
    from fastapi import HTTPException, status

    order = db.get(Order, order_id)

    if order is None or order.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return order


def _lock_order(db: Session, order_id: int) -> Order | None:
    return db.scalar(
        select(Order)
        .where(Order.id == order_id)
        .with_for_update()
    )


def _payhere_fields(order: Order, payment: Payment) -> dict[str, str]:
    parts = order.contact_name.split(maxsplit=1)
    first_name = parts[0] if parts else "Customer"
    last_name = parts[1] if len(parts) > 1 else "Customer"
    amount = f"{payment.amount:.2f}"
    merchant_id = settings.payhere_merchant_id
    signature = _payhere_signature(
        merchant_id,
        payment.reference,
        amount,
        payment.currency,
        _payhere_secret_hash(),
    )

    return {
        "merchant_id": merchant_id,
        "return_url": (
            f"{settings.frontend_base_url.rstrip('/')}"
            f"/orders/{order.id}?payment=return"
        ),
        "cancel_url": (
            f"{settings.frontend_base_url.rstrip('/')}"
            f"/orders/{order.id}?payment=cancel"
        ),
        "notify_url": (
            f"{settings.backend_public_url.rstrip('/')}"
            "/payments/payhere/notify"
        ),
        "order_id": payment.reference,
        "items": f"FURZY order #{order.id}",
        "currency": payment.currency,
        "amount": amount,
        "first_name": first_name,
        "last_name": last_name,
        "email": order.contact_email,
        "phone": order.phone,
        "address": (
            f"{order.address_line1} {order.address_line2}".strip()
        ),
        "city": order.city,
        "country": order.country,
        "hash": signature,
    }


def create_session(
    db: Session, user: User, order_id: int
) -> PaymentSessionOut:
    from fastapi import HTTPException, status

    order = _require_order(db, user, order_id)
    provider = settings.normalized_payment_provider

    if not settings.online_payments_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Online payments are not configured.",
        )

    if provider not in {"payhere", "mock"}:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Online payments are not configured.",
        )

    locked_order = _lock_order(db, order.id)

    if locked_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    order = locked_order

    if order.payment_method != "online":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This order does not use online payment.",
        )

    if order.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This order has been cancelled.",
        )

    if order.payment_status == "paid":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This order is already paid.",
        )

    if order.payment_status == "chargedback":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This order has a chargedback payment.",
        )

    reference = f"FURZY-{order.id}-{uuid4().hex[:12].upper()}"
    payment = Payment(
        order_id=order.id,
        provider=provider,
        reference=reference,
        amount=order.total,
        currency=settings.payment_currency.strip().upper(),
        status="pending",
    )
    db.add(payment)
    db.flush()
    record_event(
        db,
        payment,
        status="pending",
        source="session",
        note="Hosted checkout session created.",
    )
    db.commit()
    db.refresh(payment)

    if provider == "payhere":
        action_url = (
            PAYHERE_SANDBOX_URL
            if settings.payhere_sandbox
            else PAYHERE_LIVE_URL
        )
        fields = _payhere_fields(order, payment)
        mock = False
    else:
        action_url = None
        fields = {}
        mock = True

    return PaymentSessionOut(
        provider=provider,
        reference=payment.reference,
        order_id=order.id,
        amount=payment.amount,
        currency=payment.currency,
        action_url=action_url,
        fields=fields,
        mock=mock,
    )


def complete_mock_payment(
    db: Session, user: User, order_id: int
) -> PaymentCompletionResult:
    from fastapi import HTTPException, status

    if (
        settings.normalized_payment_provider != "mock"
        or not settings.payment_mock_enabled
        or settings.is_production
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mock payments are not available.",
        )

    order = _require_order(db, user, order_id)
    locked_order = _lock_order(db, order.id)

    if locked_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    order = locked_order

    if order.payment_method != "online":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This order does not use online payment.",
        )

    if order.payment_status == "chargedback":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This order has a chargedback payment.",
        )

    if order.status == "cancelled" or order.stock_released_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This order has expired or was cancelled.",
        )

    payment = db.scalar(
        select(Payment)
        .where(
            Payment.order_id == order.id,
            Payment.provider == "mock",
            Payment.status == "pending",
        )
        .order_by(Payment.id.desc())
        .with_for_update()
    )

    if payment is None:
        paid_payment = db.scalar(
            select(Payment)
            .where(
                Payment.order_id == order.id,
                Payment.provider == "mock",
                Payment.status == "paid",
            )
            .order_by(Payment.id.desc())
        )

        if paid_payment is not None and order.payment_status == "paid":
            return PaymentCompletionResult(
                order_id=order.id,
                reference=paid_payment.reference,
                status=paid_payment.status,
                newly_paid=False,
                contact_email=order.contact_email,
                contact_name=order.contact_name,
                total=order.total,
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending mock payment was found.",
        )

    payment.status = "paid"
    payment.paid_at = utcnow()
    payment.provider_payment_id = f"mock-{payment.id}"
    order.payment_status = "paid"
    record_event(
        db,
        payment,
        status="paid",
        source="mock",
        status_code="mock",
        note="Mock payment completed.",
    )
    db.commit()

    return PaymentCompletionResult(
        order_id=order.id,
        reference=payment.reference,
        status=payment.status,
        newly_paid=True,
        contact_email=order.contact_email,
        contact_name=order.contact_name,
        total=order.total,
    )


def process_payhere_notification(
    db: Session, payload: dict[str, str]
) -> PaymentNotificationResult:
    from fastapi import HTTPException, status

    provider = settings.normalized_payment_provider

    if provider != "payhere" or not settings.online_payments_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PayHere is not configured.",
        )

    merchant_id = payload.get("merchant_id", "").strip()
    order_id = payload.get("order_id", "").strip()
    amount_value = payload.get("payhere_amount", "").strip()
    currency = payload.get("payhere_currency", "").strip().upper()
    status_code = payload.get("status_code", "").strip()
    md5sig = payload.get("md5sig", "").strip().upper()

    if merchant_id != settings.payhere_merchant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid merchant.",
        )

    secret_hash = _payhere_secret_hash()
    expected_signature = _payhere_notification_signature(
        merchant_id,
        order_id,
        amount_value,
        currency,
        status_code,
        secret_hash,
    )

    if not hmac.compare_digest(expected_signature, md5sig):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment signature.",
        )

    payment_lookup = db.scalar(
        select(Payment).where(Payment.reference == order_id)
    )

    if payment_lookup is None:
        logger.warning(
            "PayHere notification for an unknown payment reference."
        )
        return PaymentNotificationResult(
            response_status="ignored", reference=order_id
        )

    # Lock the order before the payment so this path uses the same lock
    # order as reservation expiry and manual reconciliation.
    order = db.scalar(
        select(Order)
        .where(Order.id == payment_lookup.order_id)
        .with_for_update()
    )
    payment = db.scalar(
        select(Payment)
        .where(Payment.reference == order_id)
        .with_for_update()
    )

    if payment is None:
        return PaymentNotificationResult(
            response_status="ignored", reference=order_id
        )

    if currency != payment.currency:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment currency mismatch.",
        )

    try:
        paid_amount = Decimal(amount_value)
    except (InvalidOperation, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment amount.",
        )

    if paid_amount != Decimal(payment.amount):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment amount mismatch.",
        )

    next_status = PAYHERE_STATUS_MAP.get(status_code)

    if next_status is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown payment status.",
        )

    provider_payment_id = payload.get(
        "payment_id", payment.provider_payment_id
    )

    if payment.status == "chargedback":
        if next_status == "chargedback":
            return PaymentNotificationResult(
                response_status="ok",
                order_id=order.id if order else None,
                reference=payment.reference,
            )

        return PaymentNotificationResult(
            response_status="ignored",
            order_id=order.id if order else None,
            reference=payment.reference,
        )

    if payment.status == "paid" and next_status != "paid":
        if next_status != "chargedback":
            return PaymentNotificationResult(
                response_status="ignored",
                order_id=order.id if order else None,
                reference=payment.reference,
            )

        payment.status = "chargedback"
        payment.provider_payment_id = provider_payment_id

        if order is not None:
            order.payment_status = "chargedback"

        record_event(
            db,
            payment,
            status="chargedback",
            source="payhere",
            status_code=status_code,
            provider_payment_id=provider_payment_id,
            note="PayHere chargeback notification.",
        )
        db.commit()
        logger.info(
            "Processed PayHere chargeback for order %s.",
            payment.order_id,
        )
        return PaymentNotificationResult(
            response_status="ok",
            order_id=order.id if order else None,
            reference=payment.reference,
        )

    if next_status == "chargedback":
        return PaymentNotificationResult(
            response_status="ignored",
            order_id=order.id if order else None,
            reference=payment.reference,
        )

    if next_status == "paid":
        if payment.status == "paid":
            payment.provider_payment_id = provider_payment_id
            db.commit()
            return PaymentNotificationResult(
                response_status="ok",
                order_id=order.id if order else None,
                reference=payment.reference,
            )

        payment.status = "paid"
        payment.provider_payment_id = provider_payment_id

        if payment.paid_at is None:
            payment.paid_at = utcnow()

        if order is not None:
            order.payment_status = "paid"

        record_event(
            db,
            payment,
            status="paid",
            source="payhere",
            status_code=status_code,
            provider_payment_id=provider_payment_id,
            note="PayHere payment completed.",
        )
        db.commit()
        logger.info(
            "Processed PayHere payment for order %s.",
            payment.order_id,
        )
        return PaymentNotificationResult(
            response_status="ok",
            newly_paid=True,
            order_id=order.id if order else None,
            contact_email=order.contact_email if order else "",
            contact_name=order.contact_name if order else "",
            total=order.total if order else payment.amount,
            reference=payment.reference,
        )

    if next_status == "pending":
        if payment.status != "pending":
            return PaymentNotificationResult(
                response_status="ignored",
                order_id=order.id if order else None,
                reference=payment.reference,
            )

        return PaymentNotificationResult(
            response_status="ok",
            order_id=order.id if order else None,
            reference=payment.reference,
        )

    if payment.status in {"paid", "chargedback"}:
        return PaymentNotificationResult(
            response_status="ignored",
            order_id=order.id if order else None,
            reference=payment.reference,
        )

    if payment.status == next_status:
        return PaymentNotificationResult(
            response_status="ok",
            order_id=order.id if order else None,
            reference=payment.reference,
        )

    payment.status = next_status
    payment.provider_payment_id = provider_payment_id

    if order is not None and order.payment_status not in {
        "paid",
        "chargedback",
    }:
        order.payment_status = "failed"

    record_event(
        db,
        payment,
        status=next_status,
        source="payhere",
        status_code=status_code,
        provider_payment_id=provider_payment_id,
        note=f"PayHere notification: {next_status}.",
    )
    db.commit()
    logger.info(
        "Processed PayHere notification for order %s with status %s.",
        payment.order_id,
        next_status,
    )

    return PaymentNotificationResult(
        response_status="ok",
        order_id=order.id if order else None,
        reference=payment.reference,
    )


def list_order_payments(
    db: Session, order_id: int
) -> list[Payment]:
    return list(
        db.scalars(
            select(Payment)
            .where(Payment.order_id == order_id)
            .options(selectinload(Payment.events))
            .order_by(Payment.id.desc())
        ).all()
    )


def reconcile_payment(
    db: Session,
    admin_user: User,
    order: Order,
    payment_id: int,
    payload: ManualReconciliationRequest,
) -> ReconciliationResult:
    from fastapi import HTTPException, status

    locked_order = db.scalar(
        select(Order)
        .where(Order.id == order.id)
        .with_for_update()
    )

    if locked_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )

    order = locked_order
    payment = db.scalar(
        select(Payment)
        .where(
            Payment.id == payment_id,
            Payment.order_id == order.id,
        )
        .with_for_update()
    )

    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found for this order.",
        )

    current_status = payment.status
    next_status = payload.status

    if next_status == current_status:
        if next_status == "paid" and payload.provider_payment_id:
            payment.provider_payment_id = (
                payload.provider_payment_id.strip()
            )
            db.commit()

        return ReconciliationResult(
            payment=payment,
            newly_paid=False,
            order=order,
        )

    if current_status == "chargedback":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Chargedback payments are final.",
        )

    if current_status == "paid" and next_status in {
        "failed",
        "cancelled",
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A paid payment cannot be marked failed or cancelled; "
                "use chargedback for a post-payment reversal."
            ),
        )

    if next_status == "chargedback" and current_status != "paid":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A chargeback requires a paid payment.",
        )

    payment.status = next_status
    payment.provider_payment_id = (
        payload.provider_payment_id.strip()
        or payment.provider_payment_id
    )

    if next_status == "paid" and payment.paid_at is None:
        payment.paid_at = utcnow()

    if next_status == "paid":
        order.payment_status = "paid"
    elif next_status == "chargedback":
        order.payment_status = "chargedback"
    elif order.payment_status not in {"paid", "chargedback"}:
        order.payment_status = next_status

    record_event(
        db,
        payment,
        status=next_status,
        source="manual",
        status_code="manual",
        provider_payment_id=payment.provider_payment_id,
        note=payload.note.strip(),
        actor_user_id=admin_user.id,
    )
    db.commit()

    loaded = db.scalar(
        select(Payment)
        .where(Payment.id == payment.id)
        .options(selectinload(Payment.events))
    )

    return ReconciliationResult(
        payment=loaded or payment,
        newly_paid=next_status == "paid",
        order=order,
    )
