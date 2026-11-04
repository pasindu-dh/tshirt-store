import csv
import io
from datetime import datetime, timezone

from app.database import SessionLocal
from app.models import Order


def _add_to_cart(client, headers, product, quantity=1):
    response = client.post(
        "/cart/items",
        headers=headers,
        json={
            "variant_id": product["variants"][0]["id"],
            "quantity": quantity,
        },
    )
    assert response.status_code == 200, response.text


def _create_order(
    client,
    customer_auth,
    product,
    order_payload,
    *,
    payment_method="cod",
    quantity=1,
):
    _add_to_cart(
        client, customer_auth["headers"], product, quantity
    )
    response = client.post(
        "/orders",
        headers=customer_auth["headers"],
        json={**order_payload, "payment_method": payment_method},
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


def _parse_csv(response):
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/csv")
    return list(csv.reader(io.StringIO(response.text)))


def _set_order_date(order_id, value):
    with SessionLocal() as db:
        order = db.get(Order, order_id)
        order.created_at = value
        db.commit()


def test_order_customer_and_stock_movement_exports(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
):
    order = _create_order(
        client,
        customer_auth,
        product,
        order_payload,
        quantity=2,
    )
    _deliver_order(client, admin_auth, order)

    orders_csv = _parse_csv(
        client.get(
            "/admin/exports/orders.csv",
            headers=admin_auth["headers"],
        )
    )
    headers = orders_csv[0]
    assert "order_id" in headers
    assert "item_quantity" in headers
    order_row = next(
        row
        for row in orders_csv[1:]
        if row[headers.index("order_id")] == str(order["id"])
    )
    assert (
        order_row[headers.index("item_product")]
        == product["name"]
    )
    assert (
        order_row[headers.index("item_quantity")] == "2"
    )
    assert order_row[headers.index("status")] == "delivered"

    cancelled_csv = _parse_csv(
        client.get(
            "/admin/exports/orders.csv",
            headers=admin_auth["headers"],
            params={"status": "cancelled"},
        )
    )
    assert cancelled_csv == [headers]

    customers_csv = _parse_csv(
        client.get(
            "/admin/exports/customers.csv",
            headers=admin_auth["headers"],
        )
    )
    customer_headers = customers_csv[0]
    assert len(customers_csv) == 2
    customer_row = customers_csv[1]
    assert (
        customer_row[customer_headers.index("email")]
        == customer_auth["user"]["email"]
    )
    assert (
        customer_row[customer_headers.index("net_spend")]
        == str(order["total"])
    )

    stock_csv = _parse_csv(
        client.get(
            "/admin/exports/stock-movements.csv",
            headers=admin_auth["headers"],
        )
    )
    stock_headers = stock_csv[0]
    placed = next(
        row
        for row in stock_csv[1:]
        if row[stock_headers.index("movement_type")]
        == "order_placed"
    )
    assert placed[stock_headers.index("quantity_delta")] == "-2"
    assert placed[stock_headers.index("order_id")] == str(
        order["id"]
    )


def test_return_and_refund_exports(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
):
    order = _create_order(
        client,
        customer_auth,
        product,
        order_payload,
        payment_method="online",
    )
    session = client.post(
        f"/payments/orders/{order['id']}/session",
        headers=customer_auth["headers"],
    )
    complete = client.post(
        f"/payments/orders/{order['id']}/mock-complete",
        headers=customer_auth["headers"],
    )
    assert session.status_code == 200
    assert complete.status_code == 200
    _deliver_order(client, admin_auth, order)

    payment = client.get(
        f"/admin/orders/{order['id']}/payments",
        headers=admin_auth["headers"],
    ).json()[0]
    refund = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/refunds",
        headers=admin_auth["headers"],
        json={
            "kind": "refund",
            "amount": 1000,
            "reason": "Export test refund.",
        },
    )
    assert refund.status_code == 201
    refund_id = refund.json()["id"]
    marked = client.patch(
        f"/admin/orders/{order['id']}/refunds/{refund_id}",
        headers=admin_auth["headers"],
        json={"status": "refunded", "note": "Completed."},
    )
    assert marked.status_code == 200

    return_request = client.post(
        f"/orders/{order['id']}/returns",
        headers=customer_auth["headers"],
        json={
            "reason": "Export test return.",
            "items": [
                {
                    "order_item_id": order["items"][0]["id"],
                    "quantity": 1,
                }
            ],
        },
    )
    assert return_request.status_code == 201

    returns_csv = _parse_csv(
        client.get(
            "/admin/exports/returns.csv",
            headers=admin_auth["headers"],
        )
    )
    return_headers = returns_csv[0]
    return_row = returns_csv[1]
    assert (
        return_row[return_headers.index("return_id")]
        == str(return_request.json()["id"])
    )
    assert return_row[return_headers.index("status")] == "requested"
    assert (
        return_row[return_headers.index("refund_id")] == ""
    )

    refunds_csv = _parse_csv(
        client.get(
            "/admin/exports/refunds.csv",
            headers=admin_auth["headers"],
        )
    )
    refund_headers = refunds_csv[0]
    refund_row = refunds_csv[1]
    assert refund_row[refund_headers.index("refund_id")] == str(
        refund_id
    )
    assert refund_row[refund_headers.index("amount")] == "1000"
    assert (
        refund_row[refund_headers.index("status")] == "refunded"
    )

    filtered_refunds = _parse_csv(
        client.get(
            "/admin/exports/refunds.csv",
            headers=admin_auth["headers"],
            params={"kind": "return"},
        )
    )
    assert filtered_refunds == [refund_headers]


def test_financial_export_uses_order_dates(
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
    _set_order_date(
        order["id"],
        datetime(2026, 5, 12, 9, 0, tzinfo=timezone.utc),
    )

    response = client.get(
        "/admin/exports/financial.csv",
        headers=admin_auth["headers"],
        params={
            "date_from": "2026-05-01",
            "date_to": "2026-05-31",
            "group_by": "day",
        },
    )
    rows = _parse_csv(response)
    headers = rows[0]
    assert rows[1][headers.index("period")] == "2026-05-12"
    assert (
        rows[1][headers.index("delivered_orders")] == "1"
    )
    assert (
        rows[1][headers.index("gross_revenue")]
        == str(order["total"])
    )
    assert rows[1][headers.index("net_revenue")] == str(
        order["total"]
    )
    assert "attachment" in response.headers[
        "content-disposition"
    ]


def test_export_access_and_date_validation(
    client,
    admin_auth,
    customer_auth,
):
    customer_access = client.get(
        "/admin/exports/orders.csv",
        headers=customer_auth["headers"],
    )
    anonymous_access = client.get(
        "/admin/exports/orders.csv"
    )
    invalid_range = client.get(
        "/admin/exports/refunds.csv",
        headers=admin_auth["headers"],
        params={
            "date_from": "2026-06-01",
            "date_to": "2026-05-01",
        },
    )
    invalid_status = client.get(
        "/admin/exports/returns.csv",
        headers=admin_auth["headers"],
        params={"status": "not-a-status"},
    )

    assert customer_access.status_code == 403
    assert anonymous_access.status_code == 401
    assert invalid_range.status_code == 400
    assert invalid_status.status_code == 422
