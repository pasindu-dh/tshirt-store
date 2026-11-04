import hashlib
import hmac
import logging
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Order, Payment, User
from app.models.common import utcnow
from app.schemas.payment import (
    PaymentConfigOut,
    PaymentSessionOut,
    PaymentStatusOut,
)

logger = logging.getLogger("furzy.payments")

PAYHERE_SANDBOX_URL = "https://sandbox.payhere.lk/pay/checkout"
PAYHERE_LIVE_URL = "https://www.payhere.lk/pay/checkout"


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
            provider == "mock" and settings.payment_mock_enabled
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

    if not settings.online_payments_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Online payments are not configured.",
        )

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

    provider = settings.normalized_payment_provider
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
    elif provider == "mock":
        action_url = None
        fields = {}
        mock = True
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Online payments are not configured.",
        )

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
) -> PaymentStatusOut:
    from fastapi import HTTPException, status

    if (
        settings.normalized_payment_provider != "mock"
        or not settings.payment_mock_enabled
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mock payments are not available.",
        )

    order = _require_order(db, user, order_id)

    payment = db.scalar(
        select(Payment)
        .where(
            Payment.order_id == order.id,
            Payment.provider == "mock",
            Payment.status == "pending",
        )
        .order_by(Payment.id.desc())
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
            return PaymentStatusOut(
                order_id=order.id,
                reference=paid_payment.reference,
                status=paid_payment.status,
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending mock payment was found.",
        )

    payment.status = "paid"
    payment.paid_at = utcnow()
    payment.provider_payment_id = f"mock-{payment.id}"
    order.payment_status = "paid"
    db.commit()

    return PaymentStatusOut(
        order_id=order.id,
        reference=payment.reference,
        status=payment.status,
    )


def process_payhere_notification(
    db: Session, payload: dict[str, str]
) -> dict[str, str]:
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

    payment = db.scalar(
        select(Payment).where(Payment.reference == order_id)
    )

    if payment is None:
        logger.warning(
            "PayHere notification for an unknown payment reference."
        )
        return {"status": "ignored"}

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

    status_map = {
        "2": "paid",
        "0": "pending",
        "-1": "cancelled",
        "-2": "failed",
        "-3": "chargedback",
    }
    next_status = status_map.get(status_code)

    if next_status is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown payment status.",
        )

    order = db.get(Order, payment.order_id)

    if payment.status == "paid" and next_status != "paid":
        return {"status": "ignored"}

    payment.provider_payment_id = payload.get(
        "payment_id", payment.provider_payment_id
    )

    if next_status == "paid":
        payment.status = "paid"

        if payment.paid_at is None:
            payment.paid_at = utcnow()

        if order is not None:
            order.payment_status = "paid"
    elif next_status in {"failed", "cancelled", "chargedback"}:
        payment.status = next_status
        if order is not None and order.payment_status != "paid":
            order.payment_status = "failed"
    else:
        payment.status = "pending"

    db.commit()
    logger.info(
        "Processed PayHere notification for order %s with status %s.",
        payment.order_id,
        next_status,
    )

    return {"status": "ok"}
