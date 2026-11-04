from collections import defaultdict
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Order, Refund, ReturnItem, ReturnRequest
from app.schemas.reporting import (
    FinancialPeriodOut,
    FinancialReportOut,
    FinancialSummaryOut,
    RefundStatusBreakdownOut,
    ReturnStatusBreakdownOut,
)

# A paid or fully refunded delivered order contributes to gross revenue.
# Chargebacks and unpaid/cancelled orders are excluded.
REVENUE_PAYMENT_STATUSES = ("paid", "refunded")
PENDING_REFUND_STATUSES = ("pending", "processing")
REFUND_STATUSES = ("pending", "processing", "refunded", "failed")
RETURN_STATUSES = (
    "requested",
    "approved",
    "rejected",
    "completed",
    "cancelled",
)


def _date_filters(
    column,
    date_from: date | None,
    date_to: date | None,
) -> list:
    filters = []

    if date_from is not None:
        filters.append(
            column >= datetime.combine(date_from, time.min)
        )

    if date_to is not None:
        filters.append(
            column
            < datetime.combine(
                date_to + timedelta(days=1), time.min
            )
        )

    return filters


def _period_key(value: datetime, group_by: str) -> str:
    if group_by == "day":
        return value.strftime("%Y-%m-%d")

    return value.strftime("%Y-%m")


def financial_report(
    db: Session,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    group_by: str = "month",
) -> FinancialReportOut:
    order_filters = [
        Order.status == "delivered",
        Order.payment_status.in_(REVENUE_PAYMENT_STATUSES),
        *_date_filters(Order.created_at, date_from, date_to),
    ]
    orders = db.execute(
        select(
            Order.id, Order.total, Order.created_at
        ).where(*order_filters)
    ).all()
    orders_by_id = {row.id: row for row in orders}

    refund_rows = []

    if orders_by_id:
        refund_rows = db.execute(
            select(
                Refund.order_id,
                Refund.amount,
                Refund.status,
            ).where(Refund.order_id.in_(list(orders_by_id)))
        ).all()

    periods: dict[str, dict] = {}

    for order in orders:
        key = _period_key(order.created_at, group_by)
        entry = periods.setdefault(
            key,
            {
                "period": key,
                "delivered_orders": 0,
                "gross_revenue": 0,
                "refunded_total": 0,
                "net_revenue": 0,
            },
        )
        entry["delivered_orders"] += 1
        entry["gross_revenue"] += int(order.total)

    refund_status_counts = defaultdict(int)
    refund_status_amounts = defaultdict(int)
    refunded_total = 0
    pending_refund_total = 0

    for refund in refund_rows:
        amount = int(refund.amount)
        refund_status_counts[refund.status] += 1
        refund_status_amounts[refund.status] += amount

        if refund.status == "refunded":
            refunded_total += amount
            order = orders_by_id[refund.order_id]
            key = _period_key(order.created_at, group_by)
            periods[key]["refunded_total"] += amount
        elif refund.status in PENDING_REFUND_STATUSES:
            pending_refund_total += amount

    gross_revenue = sum(int(order.total) for order in orders)
    period_list = []

    for key in sorted(periods):
        entry = periods[key]
        entry["net_revenue"] = (
            entry["gross_revenue"] - entry["refunded_total"]
        )
        period_list.append(FinancialPeriodOut(**entry))

    return_filters = _date_filters(
        ReturnRequest.created_at, date_from, date_to
    )
    return_counts = dict(
        db.execute(
            select(
                ReturnRequest.status,
                func.count(ReturnRequest.id),
            )
            .where(*return_filters)
            .group_by(ReturnRequest.status)
        ).all()
    )
    returned_units = int(
        db.scalar(
            select(
                func.coalesce(func.sum(ReturnItem.quantity), 0)
            )
            .join(
                ReturnRequest,
                ReturnItem.return_request_id == ReturnRequest.id,
            )
            .where(
                ReturnRequest.status == "completed",
                *return_filters,
            )
        )
        or 0
    )

    summary = FinancialSummaryOut(
        gross_revenue=gross_revenue,
        refunded_total=refunded_total,
        pending_refund_total=pending_refund_total,
        net_revenue=gross_revenue - refunded_total,
        delivered_orders=len(orders),
        refund_count=len(refund_rows),
        refunded_count=refund_status_counts.get("refunded", 0),
        returns_total=sum(return_counts.values()),
        open_returns=(
            return_counts.get("requested", 0)
            + return_counts.get("approved", 0)
        ),
        completed_returns=return_counts.get("completed", 0),
        returned_units=returned_units,
    )

    return FinancialReportOut(
        date_from=date_from,
        date_to=date_to,
        group_by=group_by,
        summary=summary,
        periods=period_list,
        refund_statuses=[
            RefundStatusBreakdownOut(
                status=status,
                count=refund_status_counts.get(status, 0),
                amount=refund_status_amounts.get(status, 0),
            )
            for status in REFUND_STATUSES
        ],
        return_statuses=[
            ReturnStatusBreakdownOut(
                status=status,
                count=return_counts.get(status, 0),
            )
            for status in RETURN_STATUSES
        ],
    )
