from datetime import date, datetime, time, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import (
    Category,
    Order,
    OrderItem,
    Product,
    ProductVariant,
    ReturnItem,
    ReturnRequest,
)
from app.schemas.product_report import (
    CategoryPerformanceOut,
    ProductPerformanceOut,
    ProductPerformanceReportOut,
    ProductPerformanceSummaryOut,
)
from app.services.reporting import REVENUE_PAYMENT_STATUSES


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


def _product_key(
    product_id: int | None,
    product_name: str,
    product_slug: str,
) -> int | str:
    if product_id is not None:
        return product_id

    return f"deleted:{product_name}:{product_slug}"


def _return_rate(returned_units: int, units_sold: int) -> float:
    if units_sold <= 0:
        return 0.0

    return round(returned_units / units_sold * 100, 2)


def product_performance(
    db: Session,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 20,
) -> ProductPerformanceReportOut:
    order_filters = [
        Order.status == "delivered",
        Order.payment_status.in_(REVENUE_PAYMENT_STATUSES),
        *_date_filters(Order.created_at, date_from, date_to),
    ]

    rows = db.execute(
        select(
            OrderItem.product_id,
            OrderItem.product_name,
            OrderItem.product_slug,
            OrderItem.quantity,
            OrderItem.line_total,
            OrderItem.order_id,
            Product.category_id,
            Category.name.label("category_name"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .outerjoin(Product, OrderItem.product_id == Product.id)
        .outerjoin(
            Category, Product.category_id == Category.id
        )
        .where(*order_filters)
    ).all()

    products: dict[int | str, dict] = {}

    for row in rows:
        key = _product_key(
            row.product_id,
            row.product_name,
            row.product_slug,
        )
        entry = products.setdefault(
            key,
            {
                "product_id": row.product_id,
                "product_name": row.product_name,
                "product_slug": row.product_slug,
                "category_id": row.category_id,
                "category_name": (
                    row.category_name or "Uncategorized"
                ),
                "units_sold": 0,
                "order_ids": set(),
                "gross_revenue": 0,
                "returned_units": 0,
                "current_stock": 0,
                "stock_value": 0,
                "low_stock_variants": 0,
            },
        )
        entry["units_sold"] += int(row.quantity)
        entry["gross_revenue"] += int(row.line_total)
        entry["order_ids"].add(row.order_id)

    return_rows = db.execute(
        select(
            OrderItem.product_id,
            OrderItem.product_name,
            OrderItem.product_slug,
            ReturnItem.quantity,
        )
        .join(
            ReturnRequest,
            ReturnItem.return_request_id == ReturnRequest.id,
        )
        .join(
            Order,
            ReturnRequest.order_id == Order.id,
        )
        .join(
            OrderItem,
            ReturnItem.order_item_id == OrderItem.id,
        )
        .where(
            ReturnRequest.status == "completed",
            *order_filters,
        )
    ).all()

    for returned in return_rows:
        key = _product_key(
            returned.product_id,
            returned.product_name,
            returned.product_slug,
        )
        entry = products.get(key)

        if entry is not None:
            entry["returned_units"] += int(returned.quantity)

    stock_rows = db.execute(
        select(
            ProductVariant.product_id,
            Product.price,
            func.coalesce(
                func.sum(ProductVariant.stock), 0
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            ProductVariant.stock
                            <= ProductVariant.low_stock_threshold,
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (ProductVariant.stock <= 0, 1),
                        else_=0,
                    )
                ),
                0,
            ),
        )
        .join(Product, ProductVariant.product_id == Product.id)
        .where(Product.is_active.is_(True))
        .group_by(ProductVariant.product_id, Product.price)
    ).all()

    stock_by_product = {}
    current_stock_value = 0
    low_stock_variants = 0
    out_of_stock_variants = 0

    for row in stock_rows:
        (
            product_id,
            price,
            stock,
            low_count,
            out_count,
        ) = row
        stock_value = int(stock) * int(price)
        stock_by_product[product_id] = {
            "stock": int(stock),
            "stock_value": stock_value,
            "low_stock_variants": int(low_count),
        }
        current_stock_value += stock_value
        low_stock_variants += int(low_count)
        out_of_stock_variants += int(out_count)

    for product in products.values():
        stock = stock_by_product.get(product["product_id"])

        if stock is not None:
            product["current_stock"] = stock["stock"]
            product["stock_value"] = stock["stock_value"]
            product["low_stock_variants"] = stock[
                "low_stock_variants"
            ]

    categories: dict[int | str, dict] = {}

    for product in products.values():
        key = (
            product["category_id"]
            if product["category_id"] is not None
            else "uncategorized"
        )
        entry = categories.setdefault(
            key,
            {
                "category_id": product["category_id"],
                "category_name": product["category_name"],
                "product_keys": set(),
                "units_sold": 0,
                "gross_revenue": 0,
            },
        )
        entry["product_keys"].add(
            _product_key(
                product["product_id"],
                product["product_name"],
                product["product_slug"],
            )
        )
        entry["units_sold"] += product["units_sold"]
        entry["gross_revenue"] += product["gross_revenue"]

    category_list = [
        CategoryPerformanceOut(
            category_id=entry["category_id"],
            category_name=entry["category_name"],
            product_count=len(entry["product_keys"]),
            units_sold=entry["units_sold"],
            gross_revenue=entry["gross_revenue"],
        )
        for entry in categories.values()
    ]
    category_list.sort(
        key=lambda item: (
            -item.gross_revenue,
            -item.units_sold,
            item.category_name.lower(),
        )
    )

    product_list = [
        ProductPerformanceOut(
            product_id=product["product_id"],
            product_name=product["product_name"],
            product_slug=product["product_slug"],
            category_id=product["category_id"],
            category_name=product["category_name"],
            units_sold=product["units_sold"],
            order_count=len(product["order_ids"]),
            gross_revenue=product["gross_revenue"],
            returned_units=product["returned_units"],
            return_rate=_return_rate(
                product["returned_units"],
                product["units_sold"],
            ),
            current_stock=product["current_stock"],
            stock_value=product["stock_value"],
            low_stock_variants=product[
                "low_stock_variants"
            ],
        )
        for product in products.values()
    ]
    product_list.sort(
        key=lambda item: (
            -item.gross_revenue,
            -item.units_sold,
            item.product_name.lower(),
        )
    )

    units_sold = sum(
        product["units_sold"] for product in products.values()
    )
    gross_revenue = sum(
        product["gross_revenue"]
        for product in products.values()
    )
    returned_units = sum(
        product["returned_units"]
        for product in products.values()
    )

    summary = ProductPerformanceSummaryOut(
        units_sold=units_sold,
        gross_revenue=gross_revenue,
        returned_units=returned_units,
        return_rate=_return_rate(returned_units, units_sold),
        products_sold=len(products),
        current_stock_value=current_stock_value,
        low_stock_variants=low_stock_variants,
        out_of_stock_variants=out_of_stock_variants,
    )

    return ProductPerformanceReportOut(
        date_from=date_from,
        date_to=date_to,
        summary=summary,
        products=product_list[:limit],
        categories=category_list,
    )
