from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Order, Refund, ReturnRequest, User
from app.schemas.customer import (
    AdminCustomerDetailOut,
    AdminCustomerOut,
)
from app.services.reporting import (
    PENDING_REFUND_STATUSES,
    REVENUE_PAYMENT_STATUSES,
)

CUSTOMER_ORDER_LIMIT = 100
CUSTOMER_RETURN_LIMIT = 100


def _empty_stats() -> dict:
    return {
        "order_count": 0,
        "delivered_orders": 0,
        "cancelled_orders": 0,
        "gross_spend": 0,
        "refunded_total": 0,
        "pending_refund_total": 0,
        "net_spend": 0,
        "returns_count": 0,
        "open_returns": 0,
        "last_order_at": None,
    }


def _stats_for_users(
    db: Session, user_ids: list[int]
) -> dict[int, dict]:
    stats = {
        user_id: _empty_stats() for user_id in user_ids
    }

    if not user_ids:
        return stats

    order_rows = db.execute(
        select(
            Order.user_id,
            Order.status,
            Order.payment_status,
            Order.total,
            Order.created_at,
        ).where(Order.user_id.in_(user_ids))
    ).all()

    for order in order_rows:
        entry = stats[order.user_id]
        entry["order_count"] += 1

        if order.status == "delivered":
            entry["delivered_orders"] += 1
        elif order.status == "cancelled":
            entry["cancelled_orders"] += 1

        if (
            order.status == "delivered"
            and order.payment_status
            in REVENUE_PAYMENT_STATUSES
        ):
            entry["gross_spend"] += int(order.total)

        if (
            entry["last_order_at"] is None
            or order.created_at > entry["last_order_at"]
        ):
            entry["last_order_at"] = order.created_at

    refund_rows = db.execute(
        select(
            Order.user_id,
            Refund.amount,
            Refund.status,
        )
        .join(Refund, Refund.order_id == Order.id)
        .where(
            Order.user_id.in_(user_ids),
            Order.status == "delivered",
            Order.payment_status.in_(
                REVENUE_PAYMENT_STATUSES
            ),
        )
    ).all()

    for refund in refund_rows:
        entry = stats[refund.user_id]
        amount = int(refund.amount)

        if refund.status == "refunded":
            entry["refunded_total"] += amount
        elif refund.status in PENDING_REFUND_STATUSES:
            entry["pending_refund_total"] += amount

    return_rows = db.execute(
        select(
            ReturnRequest.user_id,
            ReturnRequest.status,
        ).where(ReturnRequest.user_id.in_(user_ids))
    ).all()

    for request in return_rows:
        entry = stats[request.user_id]
        entry["returns_count"] += 1

        if request.status in {"requested", "approved"}:
            entry["open_returns"] += 1

    for entry in stats.values():
        entry["net_spend"] = (
            entry["gross_spend"] - entry["refunded_total"]
        )

    return stats


def _customer_out(
    user: User, stats: dict[int, dict]
) -> AdminCustomerOut:
    return AdminCustomerOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        created_at=user.created_at,
        **stats.get(user.id, _empty_stats()),
    )


def list_customers(
    db: Session,
    *,
    page: int,
    limit: int,
    search: str | None = None,
) -> tuple[list[AdminCustomerOut], int]:
    filters = [User.role == "customer"]

    if search and search.strip():
        term_value = search.strip()

        if term_value.isdigit():
            filters.append(
                or_(
                    User.id == int(term_value),
                    User.name.ilike(f"%{term_value}%"),
                    User.email.ilike(f"%{term_value}%"),
                )
            )
        else:
            term = f"%{term_value}%"
            filters.append(
                or_(
                    User.name.ilike(term),
                    User.email.ilike(term),
                )
            )

    total = int(
        db.scalar(
            select(func.count(User.id)).where(*filters)
        )
        or 0
    )
    users = db.scalars(
        select(User)
        .where(*filters)
        .order_by(User.created_at.desc(), User.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    stats = _stats_for_users(
        db, [user.id for user in users]
    )

    return [
        _customer_out(user, stats) for user in users
    ], total


def get_customer(
    db: Session, customer_id: int
) -> AdminCustomerDetailOut | None:
    user = db.scalar(
        select(User).where(
            User.id == customer_id,
            User.role == "customer",
        )
    )

    if user is None:
        return None

    stats = _stats_for_users(db, [user.id])
    orders = list(
        db.scalars(
            select(Order)
            .where(Order.user_id == user.id)
            .options(selectinload(Order.items))
            .order_by(
                Order.created_at.desc(), Order.id.desc()
            )
            .limit(CUSTOMER_ORDER_LIMIT)
        ).all()
    )
    returns = list(
        db.scalars(
            select(ReturnRequest)
            .where(ReturnRequest.user_id == user.id)
            .options(
                selectinload(ReturnRequest.refund),
                selectinload(ReturnRequest.items),
            )
            .order_by(ReturnRequest.id.desc())
            .limit(CUSTOMER_RETURN_LIMIT)
        ).all()
    )

    return AdminCustomerDetailOut(
        **_customer_out(user, stats).model_dump(),
        orders=orders,
        returns=returns,
    )
