from sqlalchemy.orm import Session

from app.models import Payment, PaymentEvent


def record_event(
    db: Session,
    payment: Payment,
    *,
    status: str,
    source: str,
    status_code: str = "",
    provider_payment_id: str | None = None,
    note: str = "",
    actor_user_id: int | None = None,
) -> PaymentEvent:
    event = PaymentEvent(
        payment_id=payment.id,
        status=status,
        status_code=status_code,
        provider_payment_id=(
            provider_payment_id
            if provider_payment_id is not None
            else payment.provider_payment_id
        ),
        amount=payment.amount,
        currency=payment.currency,
        source=source,
        note=note,
        actor_user_id=actor_user_id,
    )
    db.add(event)
    return event
