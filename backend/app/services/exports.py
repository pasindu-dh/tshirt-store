import csv
import io
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import Order, Product, Refund
from app.services import admin_orders, customers, inventory, reporting, returns
from app.services.catalog_import import CATALOG_HEADERS

EXPORT_LIMIT = 100000


def _dt(value: datetime | None) -> str:
    return value.isoformat() if value is not None else ""


def to_csv(headers: list[str], rows: list[list]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    return buffer.getvalue()


def order_rows(
    db: Session,
    *,
    status_filter: str | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[list[str], list[list]]:
    headers = [
        "order_id",
        "order_date",
        "status",
        "payment_method",
        "payment_status",
        "customer_name",
        "customer_email",
        "phone",
        "order_total",
        "item_product",
        "item_sku",
        "item_size",
        "item_color",
        "item_quantity",
        "item_unit_price",
        "item_line_total",
    ]
    orders, _total = admin_orders.list_orders(
        db,
        page=1,
        limit=EXPORT_LIMIT,
        status_filter=status_filter,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
    rows = []

    for order in orders:
        base = [
            order.id,
            _dt(order.created_at),
            order.status,
            order.payment_method,
            order.payment_status,
            order.contact_name,
            order.contact_email,
            order.phone,
            order.total,
        ]

        if not order.items:
            rows.append(base + ["", "", "", "", "", "", ""])
            continue

        for item in order.items:
            rows.append(
                base
                + [
                    item.product_name,
                    item.sku,
                    item.size,
                    item.color,
                    item.quantity,
                    item.unit_price,
                    item.line_total,
                ]
            )

    return headers, rows


def customer_rows(
    db: Session,
    *,
    search: str | None = None,
) -> tuple[list[str], list[list]]:
    headers = [
        "customer_id",
        "name",
        "email",
        "joined_at",
        "order_count",
        "delivered_orders",
        "cancelled_orders",
        "gross_spend",
        "refunded_total",
        "pending_refund_total",
        "net_spend",
        "returns_count",
        "open_returns",
        "last_order_at",
    ]
    customers_list, _total = customers.list_customers(
        db,
        page=1,
        limit=EXPORT_LIMIT,
        search=search,
    )
    rows = [
        [
            customer.id,
            customer.name,
            customer.email,
            _dt(customer.created_at),
            customer.order_count,
            customer.delivered_orders,
            customer.cancelled_orders,
            customer.gross_spend,
            customer.refunded_total,
            customer.pending_refund_total,
            customer.net_spend,
            customer.returns_count,
            customer.open_returns,
            _dt(customer.last_order_at),
        ]
        for customer in customers_list
    ]
    return headers, rows


def return_rows(
    db: Session,
    *,
    status_filter: str | None = None,
    search: str | None = None,
) -> tuple[list[str], list[list]]:
    headers = [
        "return_id",
        "order_id",
        "status",
        "reason",
        "created_at",
        "order_contact_name",
        "order_contact_email",
        "order_total",
        "item_count",
        "refund_id",
        "refund_status",
    ]
    returns_list, _total = returns.list_admin_returns(
        db,
        page=1,
        limit=EXPORT_LIMIT,
        status_filter=status_filter,
        search=search,
    )
    rows = [
        [
            request.id,
            request.order_id,
            request.status,
            request.reason,
            _dt(request.created_at),
            request.order_contact_name,
            request.order_contact_email,
            request.order_total,
            request.item_count,
            request.refund_id or "",
            request.refund_status or "",
        ]
        for request in returns_list
    ]
    return headers, rows


def refund_rows(
    db: Session,
    *,
    status_filter: str | None = None,
    kind: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[list[str], list[list]]:
    headers = [
        "refund_id",
        "order_id",
        "payment_id",
        "amount",
        "kind",
        "status",
        "provider",
        "provider_refund_id",
        "reason",
        "notes",
        "created_at",
        "completed_at",
        "order_contact_name",
        "order_contact_email",
    ]
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

    refunds = db.execute(
        select(
            Refund,
            Order.contact_name,
            Order.contact_email,
        )
        .join(Order, Refund.order_id == Order.id)
        .where(*filters)
        .order_by(
            Refund.created_at.desc(), Refund.id.desc()
        )
        .limit(EXPORT_LIMIT)
    ).all()

    rows = [
        [
            refund.id,
            refund.order_id,
            refund.payment_id,
            refund.amount,
            refund.kind,
            refund.status,
            refund.provider,
            refund.provider_refund_id,
            refund.reason,
            refund.notes,
            _dt(refund.created_at),
            _dt(refund.completed_at),
            contact_name,
            contact_email,
        ]
        for refund, contact_name, contact_email in refunds
    ]
    return headers, rows


def stock_movement_rows(
    db: Session,
    *,
    movement_type: str | None = None,
    variant_id: int | None = None,
    product_id: int | None = None,
    order_id: int | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[list[str], list[list]]:
    headers = [
        "movement_id",
        "created_at",
        "movement_type",
        "product_name",
        "size",
        "color",
        "sku",
        "quantity_delta",
        "stock_before",
        "stock_after",
        "reason",
        "order_id",
        "return_request_id",
        "actor_user_id",
    ]
    movements, _total = inventory.list_movements(
        db,
        page=1,
        limit=EXPORT_LIMIT,
        movement_type=movement_type,
        variant_id=variant_id,
        product_id=product_id,
        order_id=order_id,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
    rows = [
        [
            movement.id,
            _dt(movement.created_at),
            movement.movement_type,
            movement.product_name,
            movement.size,
            movement.color,
            movement.sku,
            movement.quantity_delta,
            movement.stock_before,
            movement.stock_after,
            movement.reason,
            movement.order_id or "",
            movement.return_request_id or "",
            movement.actor_user_id or "",
        ]
        for movement in movements
    ]
    return headers, rows


def catalog_rows(
    db: Session,
) -> tuple[list[str], list[list]]:
    products = db.scalars(
        select(Product)
        .options(
            joinedload(Product.category),
            selectinload(Product.images),
            selectinload(Product.variants),
        )
        .order_by(Product.id)
    ).all()
    rows = []

    for product in products:
        image_urls = "|".join(
            image.url for image in product.images
        )
        variants = product.variants or [None]

        for variant in variants:
            rows.append(
                [
                    product.slug,
                    product.name,
                    product.description,
                    product.price,
                    (
                        product.category.slug
                        if product.category
                        else ""
                    ),
                    "true" if product.is_active else "false",
                    image_urls,
                    variant.size if variant else "",
                    variant.color if variant else "",
                    variant.sku if variant else "",
                    variant.stock if variant else "",
                    (
                        variant.low_stock_threshold
                        if variant
                        else ""
                    ),
                ]
            )

    return CATALOG_HEADERS, rows


def financial_rows(
    db: Session,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    group_by: str = "month",
) -> tuple[list[str], list[list]]:
    headers = [
        "period",
        "delivered_orders",
        "gross_revenue",
        "refunded_total",
        "net_revenue",
    ]
    report = reporting.financial_report(
        db,
        date_from=date_from,
        date_to=date_to,
        group_by=group_by,
    )
    rows = [
        [
            period.period,
            period.delivered_orders,
            period.gross_revenue,
            period.refunded_total,
            period.net_revenue,
        ]
        for period in report.periods
    ]
    return headers, rows
