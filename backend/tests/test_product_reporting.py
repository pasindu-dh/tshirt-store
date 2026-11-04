from datetime import datetime, timezone

from app.database import SessionLocal
from app.models import Order


def _add_to_cart(client, headers, variant_id, quantity):
    response = client.post(
        "/cart/items",
        headers=headers,
        json={"variant_id": variant_id, "quantity": quantity},
    )
    assert response.status_code == 200, response.text


def _create_order(
    client,
    customer_auth,
    product,
    order_payload,
    quantity=1,
):
    _add_to_cart(
        client,
        customer_auth["headers"],
        product["variants"][0]["id"],
        quantity,
    )
    response = client.post(
        "/orders",
        headers=customer_auth["headers"],
        json={**order_payload, "payment_method": "cod"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _deliver_order(client, admin_auth, order):
    for status in ("confirmed", "shipped", "delivered"):
        response = client.patch(
            f"/admin/orders/{order['id']}/status",
            headers=admin_auth["headers"],
            json={"status": status},
        )
        assert response.status_code == 200, response.text


def _complete_return(
    client,
    admin_auth,
    customer_auth,
    order,
    quantity=1,
):
    response = client.post(
        f"/orders/{order['id']}/returns",
        headers=customer_auth["headers"],
        json={
            "reason": "Product performance test return.",
            "items": [
                {
                    "order_item_id": order["items"][0]["id"],
                    "quantity": quantity,
                }
            ],
        },
    )
    assert response.status_code == 201, response.text
    return_id = response.json()["id"]

    approved = client.patch(
        f"/admin/orders/{order['id']}/returns/{return_id}",
        headers=admin_auth["headers"],
        json={"status": "approved"},
    )
    completed = client.patch(
        f"/admin/orders/{order['id']}/returns/{return_id}",
        headers=admin_auth["headers"],
        json={"status": "completed"},
    )
    assert approved.status_code == 200
    assert completed.status_code == 200


def _set_order_date(order_id, value):
    with SessionLocal() as db:
        order = db.get(Order, order_id)
        order.created_at = value
        db.commit()


def _report(client, admin_auth, **params):
    response = client.get(
        "/admin/reports/products",
        headers=admin_auth["headers"],
        params=params,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_product_performance_aggregates_and_date_filters(
    client,
    admin_auth,
    customer_auth,
    create_product,
    order_payload,
):
    category = client.post(
        "/admin/categories",
        headers=admin_auth["headers"],
        json={"name": "Performance"},
    )
    assert category.status_code == 201
    category_id = category.json()["id"]

    alpha = create_product(
        name="Alpha Performance Tee",
        price=2500,
        category_id=category_id,
    )
    beta = create_product(
        name="Beta Performance Tee",
        price=3000,
        category_id=category_id,
    )

    alpha_order = _create_order(
        client,
        customer_auth,
        alpha,
        order_payload,
        quantity=2,
    )
    _deliver_order(client, admin_auth, alpha_order)
    _complete_return(
        client,
        admin_auth,
        customer_auth,
        alpha_order,
        quantity=1,
    )

    beta_order = _create_order(
        client, customer_auth, beta, order_payload, quantity=1
    )
    _deliver_order(client, admin_auth, beta_order)

    cancelled = _create_order(
        client, customer_auth, alpha, order_payload, quantity=1
    )
    cancelled_response = client.patch(
        f"/admin/orders/{cancelled['id']}/status",
        headers=admin_auth["headers"],
        json={"status": "cancelled"},
    )
    assert cancelled_response.status_code == 200

    _set_order_date(
        alpha_order["id"],
        datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc),
    )
    _set_order_date(
        beta_order["id"],
        datetime(2026, 3, 11, 10, 0, tzinfo=timezone.utc),
    )

    report = _report(
        client,
        admin_auth,
        date_from="2026-03-01",
        date_to="2026-03-31",
    )
    summary = report["summary"]
    assert summary["units_sold"] == 3
    assert summary["gross_revenue"] == 8000
    assert summary["returned_units"] == 1
    assert summary["return_rate"] == 33.33
    assert summary["products_sold"] == 2
    assert summary["current_stock_value"] == 49500
    assert summary["low_stock_variants"] == 2
    assert summary["out_of_stock_variants"] == 0

    assert [item["product_name"] for item in report["products"]] == [
        "Alpha Performance Tee",
        "Beta Performance Tee",
    ]
    alpha_row = report["products"][0]
    beta_row = report["products"][1]
    assert alpha_row["product_id"] == alpha["id"]
    assert alpha_row["category_name"] == "Performance"
    assert alpha_row["units_sold"] == 2
    assert alpha_row["order_count"] == 1
    assert alpha_row["gross_revenue"] == 5000
    assert alpha_row["returned_units"] == 1
    assert alpha_row["return_rate"] == 50.0
    assert alpha_row["current_stock"] == 9
    assert alpha_row["stock_value"] == 22500
    assert alpha_row["low_stock_variants"] == 1

    assert beta_row["product_id"] == beta["id"]
    assert beta_row["units_sold"] == 1
    assert beta_row["order_count"] == 1
    assert beta_row["gross_revenue"] == 3000
    assert beta_row["returned_units"] == 0
    assert beta_row["return_rate"] == 0.0
    assert beta_row["current_stock"] == 9
    assert beta_row["stock_value"] == 27000

    assert report["categories"] == [
        {
            "category_id": category_id,
            "category_name": "Performance",
            "product_count": 2,
            "units_sold": 3,
            "gross_revenue": 8000,
        }
    ]

    empty = _report(
        client,
        admin_auth,
        date_from="2026-02-01",
        date_to="2026-02-28",
    )
    assert empty["summary"]["units_sold"] == 0
    assert empty["summary"]["gross_revenue"] == 0
    assert empty["summary"]["products_sold"] == 0
    assert empty["summary"]["current_stock_value"] == 49500
    assert empty["products"] == []
    assert empty["categories"] == []


def test_product_performance_limits_access_and_dates(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
):
    order = _create_order(
        client, customer_auth, product, order_payload
    )
    _deliver_order(client, admin_auth, order)

    limited = client.get(
        "/admin/reports/products",
        headers=admin_auth["headers"],
        params={"limit": 1},
    )
    assert limited.status_code == 200
    assert len(limited.json()["products"]) == 1

    invalid_limit = client.get(
        "/admin/reports/products",
        headers=admin_auth["headers"],
        params={"limit": 0},
    )
    invalid_range = client.get(
        "/admin/reports/products",
        headers=admin_auth["headers"],
        params={
            "date_from": "2026-04-01",
            "date_to": "2026-03-01",
        },
    )
    customer_access = client.get(
        "/admin/reports/products",
        headers=customer_auth["headers"],
    )
    anonymous_access = client.get(
        "/admin/reports/products"
    )

    assert invalid_limit.status_code == 422
    assert invalid_range.status_code == 400
    assert customer_access.status_code == 403
    assert anonymous_access.status_code == 401
