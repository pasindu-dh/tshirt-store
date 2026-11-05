import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Order,
    OrderAuditEvent,
    Payment,
    Refund,
    ReturnRequest,
    User,
)
from app.schemas.activity import OrderActivityOut

FIELD_LABELS = {
    "contact_name": "contact name",
    "contact_email": "contact email",
    "phone": "phone",
    "address_line1": "address line 1",
    "address_line2": "address line 2",
    "city": "city",
    "postal_code": "postal code",
    "country": "country",
    "notes": "internal notes",
}


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _actor_names(db: Session, user_ids: set[int]) -> dict[int, str]:
    if not user_ids:
        return {}

    users = db.scalars(
        select(User).where(User.id.in_(sorted(user_ids)))
    ).all()

    return {user.id: user.name for user in users}


def _describe_changes(changes: dict) -> str:
    parts = []

    for field, change in changes.items():
        label = FIELD_LABELS.get(field, field.replace("_", " "))
        before = change.get("from") or "—"
        after = change.get("to") or "—"
        parts.append(f"{label}: {before} → {after}")

    return "; ".join(parts)


def build_order_activity(
    db: Session, order: Order
) -> list[OrderActivityOut]:
    audit_events = db.scalars(
        select(OrderAuditEvent)
        .where(OrderAuditEvent.order_id == order.id)
        .order_by(
            OrderAuditEvent.created_at.asc(),
            OrderAuditEvent.id.asc(),
        )
    ).all()
    payments = db.scalars(
        select(Payment)
        .where(Payment.order_id == order.id)
        .options(selectinload(Payment.events))
        .order_by(Payment.id.asc())
    ).all()
    refunds = db.scalars(
        select(Refund)
        .where(Refund.order_id == order.id)
        .order_by(Refund.id.asc())
    ).all()
    returns = db.scalars(
        select(ReturnRequest)
        .where(ReturnRequest.order_id == order.id)
        .options(
            selectinload(ReturnRequest.items),
            selectinload(ReturnRequest.refund),
        )
        .order_by(ReturnRequest.id.asc())
    ).all()

    actor_ids = {
        event.actor_user_id
        for event in audit_events
        if event.actor_user_id is not None
    }
    actor_ids.update(
        return_request.reviewed_by_user_id
        for return_request in returns
        if return_request.reviewed_by_user_id is not None
    )
    actor_ids.update(
        refund.requested_by_user_id
        for refund in refunds
        if refund.requested_by_user_id is not None
    )
    actor_ids.update(
        event.actor_user_id
        for payment in payments
        for event in payment.events
        if event.actor_user_id is not None
    )
    actor_ids.add(order.user_id)
    names = _actor_names(db, actor_ids)
    events: list[OrderActivityOut] = []

    def add(
        key: str,
        event_type: str,
        title: str,
        created_at: datetime | None,
        description: str = "",
        actor: str = "",
    ) -> None:
        if created_at is None:
            return

        events.append(
            OrderActivityOut(
                id=key,
                type=event_type,
                title=title,
                description=description,
                actor=actor,
                created_at=_as_utc(created_at),
            )
        )

    add(
        "order-created",
        "order",
        "Order placed",
        order.created_at,
        (
            f"{order.contact_name} placed an order for "
            f"LKR {order.total}."
        ),
        names.get(order.user_id, "Customer"),
    )

    status_event_seen = set()

    for event in audit_events:
        try:
            changes = json.loads(event.changes or "{}")
        except json.JSONDecodeError:
            changes = {}

        actor = (
            names.get(event.actor_user_id, "System")
            if event.actor_user_id
            else "System"
        )

        if event.action == "status_changed":
            to_status = str(changes.get("to", ""))
            from_status = str(changes.get("from", ""))
            status_event_seen.add(to_status)
            add(
                f"audit-{event.id}",
                "status",
                f"Order {to_status}",
                event.created_at,
                (
                    f"Status changed from {from_status} to "
                    f"{to_status}."
                    if from_status
                    else f"Status changed to {to_status}."
                ),
                actor,
            )
        elif event.action == "details_edited":
            add(
                f"audit-{event.id}",
                "details",
                "Order details updated",
                event.created_at,
                _describe_changes(changes),
                actor,
            )
        else:
            add(
                f"audit-{event.id}",
                "audit",
                event.action.replace("_", " ").capitalize(),
                event.created_at,
                "",
                actor,
            )

    for payment in payments:
        for event in payment.events:
            actor = (
                names.get(event.actor_user_id, "System")
                if event.actor_user_id
                else (event.source or "System").capitalize()
            )
            description = (
                f"{payment.reference} · LKR {payment.amount} · "
                f"{payment.provider}"
            )

            if event.note:
                description += f" · {event.note}"

            add(
                f"payment-event-{event.id}",
                "payment",
                f"Payment {event.status}",
                event.created_at,
                description,
                actor,
            )

    for refund in refunds:
        actor = (
            names.get(
                refund.requested_by_user_id, "Admin"
            )
            if refund.requested_by_user_id
            else "System"
        )
        add(
            f"refund-{refund.id}",
            "refund",
            f"Refund #{refund.id} recorded",
            refund.created_at,
            (
                f"{refund.kind.capitalize()} · LKR {refund.amount} · "
                f"{refund.status} · {refund.reason}"
            ),
            actor,
        )

        if refund.completed_at is not None:
            add(
                f"refund-{refund.id}-completed",
                "refund",
                f"Refund #{refund.id} completed",
                refund.completed_at,
                f"LKR {refund.amount} returned to the customer.",
                actor,
            )

    for return_request in returns:
        add(
            f"return-{return_request.id}",
            "return",
            f"Return #{return_request.id} requested",
            return_request.created_at,
            (
                f"{sum(item.quantity for item in return_request.items)} "
                f"item(s) · {return_request.reason}"
            ),
            names.get(order.user_id, "Customer"),
        )
        reviewer = (
            names.get(
                return_request.reviewed_by_user_id, "Admin"
            )
            if return_request.reviewed_by_user_id
            else "System"
        )

        if (
            return_request.reviewed_at is not None
            and return_request.status
            in {"approved", "rejected"}
        ):
            add(
                f"return-{return_request.id}-reviewed",
                "return",
                f"Return #{return_request.id} "
                f"{return_request.status}",
                return_request.reviewed_at,
                return_request.review_note,
                reviewer,
            )

        if (
            return_request.completed_at is not None
            and return_request.status == "completed"
        ):
            add(
                f"return-{return_request.id}-completed",
                "return",
                f"Return #{return_request.id} completed",
                return_request.completed_at,
                "Returned items were restocked.",
                reviewer,
            )

        if return_request.status == "cancelled":
            add(
                f"return-{return_request.id}-cancelled",
                "return",
                f"Return #{return_request.id} cancelled",
                return_request.updated_at,
                "",
                names.get(order.user_id, "Customer"),
            )

    if order.stock_released_at is not None:
        add(
            "stock-released",
            "inventory",
            "Reserved stock released",
            order.stock_released_at,
            (
                f"Reason: {order.stock_release_reason}."
                if order.stock_release_reason
                else ""
            ),
        )

    if (
        order.delivered_at is not None
        and "delivered" not in status_event_seen
    ):
        add(
            "order-delivered",
            "status",
            "Order delivered",
            order.delivered_at,
            "",
        )

    events.sort(key=lambda event: event.created_at)
    return events
