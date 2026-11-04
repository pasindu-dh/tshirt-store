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
    payment_method,
):
    _add_to_cart(
        client, customer_auth["headers"], product, 1
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


def _payment_for_order(client, admin_auth, order):
    payments = client.get(
        f"/admin/orders/{order['id']}/payments",
        headers=admin_auth["headers"],
    )
    assert payments.status_code == 200
    return payments.json()[0]


def _create_refund(
    client,
    admin_auth,
    order,
    payment,
    amount,
    *,
    mark_refunded,
):
    response = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/refunds",
        headers=admin_auth["headers"],
        json={
            "kind": "refund",
            "amount": amount,
            "reason": "Reporting test refund.",
        },
    )
    assert response.status_code == 201, response.text
    refund = response.json()

    if mark_refunded:
        completed = client.patch(
            f"/admin/orders/{order['id']}/refunds/{refund['id']}",
            headers=admin_auth["headers"],
            json={
                "status": "refunded",
                "note": "Marked completed for reporting test.",
            },
        )
        assert completed.status_code == 200, completed.text
        refund = completed.json()

    return refund


def _report(client, admin_auth, **params):
    response = client.get(
        "/admin/reports/financial",
        headers=admin_auth["headers"],
        params=params,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _set_order_date(order_id, value):
    with SessionLocal() as db:
        order = db.get(Order, order_id)
        order.created_at = value
        db.commit()


def test_partial_refund_reporting_and_date_filters(
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
        "online",
    )
    session = client.post(
        f"/payments/orders/{order['id']}/session",
        headers=customer_auth["headers"],
    )
    assert session.status_code == 200
    complete = client.post(
        f"/payments/orders/{order['id']}/mock-complete",
        headers=customer_auth["headers"],
    )
    assert complete.status_code == 200
    _deliver_order(client, admin_auth, order)
    payment = _payment_for_order(client, admin_auth, order)

    refund = _create_refund(
        client,
        admin_auth,
        order,
        payment,
        1000,
        mark_refunded=False,
    )
    _set_order_date(
        order["id"],
        datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
    )

    pending = _report(
        client,
        admin_auth,
        date_from="2026-01-15",
        date_to="2026-01-15",
        group_by="day",
    )
    assert pending["summary"]["gross_revenue"] == order["total"]
    assert pending["summary"]["refunded_total"] == 0
    assert pending["summary"]["pending_refund_total"] == 1000
    assert pending["summary"]["net_revenue"] == order["total"]
    assert pending["summary"]["delivered_orders"] == 1
    assert pending["summary"]["refund_count"] == 1
    assert pending["periods"] == [
        {
            "period": "2026-01-15",
            "delivered_orders": 1,
            "gross_revenue": order["total"],
            "refunded_total": 0,
            "net_revenue": order["total"],
        }
    ]

    refunded = client.patch(
        f"/admin/orders/{order['id']}/refunds/{refund['id']}",
        headers=admin_auth["headers"],
        json={
            "status": "refunded",
            "note": "Completed for reporting test.",
        },
    )
    assert refunded.status_code == 200, refunded.text

    completed = _report(
        client,
        admin_auth,
        date_from="2026-01-15",
        date_to="2026-01-15",
        group_by="day",
    )
    assert completed["summary"]["gross_revenue"] == order["total"]
    assert completed["summary"]["refunded_total"] == 1000
    assert completed["summary"]["pending_refund_total"] == 0
    assert completed["summary"]["net_revenue"] == order["total"] - 1000
    assert completed["summary"]["refunded_count"] == 1
    assert completed["periods"][0]["refunded_total"] == 1000
    assert completed["periods"][0]["net_revenue"] == (
        order["total"] - 1000
    )
    refunded_breakdown = {
        item["status"]: item
        for item in completed["refund_statuses"]
    }
    assert refunded_breakdown["refunded"]["count"] == 1
    assert refunded_breakdown["refunded"]["amount"] == 1000

    stats = client.get(
        "/admin/stats", headers=admin_auth["headers"]
    ).json()
    assert stats["gross_revenue"] == order["total"]
    assert stats["refunded_total"] == 1000
    assert stats["revenue"] == order["total"] - 1000

    outside_range = _report(
        client,
        admin_auth,
        date_from="2026-01-16",
        date_to="2026-01-16",
    )
    assert outside_range["summary"]["gross_revenue"] == 0
    assert outside_range["summary"]["delivered_orders"] == 0
    assert outside_range["periods"] == []

    invalid_range = client.get(
        "/admin/reports/financial",
        headers=admin_auth["headers"],
        params={
            "date_from": "2026-01-20",
            "date_to": "2026-01-10",
        },
    )
    assert invalid_range.status_code == 400

    customer = client.get(
        "/admin/reports/financial",
        headers=customer_auth["headers"],
    )
    anonymous = client.get("/admin/reports/financial")
    assert customer.status_code == 403
    assert anonymous.status_code == 401


def test_full_refund_reporting_nets_to_zero(
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
        "online",
    )
    session = client.post(
        f"/payments/orders/{order['id']}/session",
        headers=customer_auth["headers"],
    )
    assert session.status_code == 200
    complete = client.post(
        f"/payments/orders/{order['id']}/mock-complete",
        headers=customer_auth["headers"],
    )
    assert complete.status_code == 200
    _deliver_order(client, admin_auth, order)
    payment = _payment_for_order(client, admin_auth, order)

    refund = _create_refund(
        client,
        admin_auth,
        order,
        payment,
        order["total"],
        mark_refunded=True,
    )
    assert refund["status"] == "refunded"

    current_order = client.get(
        f"/orders/{order['id']}",
        headers=customer_auth["headers"],
    ).json()
    assert current_order["payment_status"] == "refunded"

    report = _report(client, admin_auth)
    summary = report["summary"]
    assert summary["gross_revenue"] == order["total"]
    assert summary["refunded_total"] == order["total"]
    assert summary["net_revenue"] == 0
    assert summary["delivered_orders"] == 1
    assert summary["refunded_count"] == 1

    stats = client.get(
        "/admin/stats", headers=admin_auth["headers"]
    ).json()
    assert stats["gross_revenue"] == order["total"]
    assert stats["refunded_total"] == order["total"]
    assert stats["revenue"] == 0


def test_reporting_tracks_returns_and_returned_units(
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
        "cod",
    )
    _deliver_order(client, admin_auth, order)

    request = client.post(
        f"/orders/{order['id']}/returns",
        headers=customer_auth["headers"],
        json={
            "reason": "Reporting test return.",
            "items": [
                {
                    "order_item_id": order["items"][0]["id"],
                    "quantity": 1,
                }
            ],
        },
    )
    assert request.status_code == 201, request.text
    request_id = request.json()["id"]

    open_report = _report(client, admin_auth)
    open_summary = open_report["summary"]
    assert open_summary["returns_total"] == 1
    assert open_summary["open_returns"] == 1
    assert open_summary["completed_returns"] == 0
    assert open_summary["returned_units"] == 0
    return_breakdown = {
        item["status"]: item["count"]
        for item in open_report["return_statuses"]
    }
    assert return_breakdown["requested"] == 1

    stats = client.get(
        "/admin/stats", headers=admin_auth["headers"]
    ).json()
    assert stats["open_returns"] == 1
    assert stats["returns_total"] == 1

    approved = client.patch(
        f"/admin/orders/{order['id']}/returns/{request_id}",
        headers=admin_auth["headers"],
        json={"status": "approved"},
    )
    assert approved.status_code == 200
    completed = client.patch(
        f"/admin/orders/{order['id']}/returns/{request_id}",
        headers=admin_auth["headers"],
        json={"status": "completed"},
    )
    assert completed.status_code == 200

    closed_report = _report(client, admin_auth)
    closed_summary = closed_report["summary"]
    assert closed_summary["returns_total"] == 1
    assert closed_summary["open_returns"] == 0
    assert closed_summary["completed_returns"] == 1
    assert closed_summary["returned_units"] == 1
    closed_breakdown = {
        item["status"]: item["count"]
        for item in closed_report["return_statuses"]
    }
    assert closed_breakdown["completed"] == 1

    stats = client.get(
        "/admin/stats", headers=admin_auth["headers"]
    ).json()
    assert stats["open_returns"] == 0
    assert stats["returns_total"] == 1


def test_financial_report_groups_by_month(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
):
    first = _create_order(
        client,
        customer_auth,
        product,
        order_payload,
        "cod",
    )
    _deliver_order(client, admin_auth, first)
    second = _create_order(
        client,
        customer_auth,
        product,
        order_payload,
        "cod",
    )
    _deliver_order(client, admin_auth, second)
    _set_order_date(
        first["id"],
        datetime(2026, 2, 10, 9, 0, tzinfo=timezone.utc),
    )
    _set_order_date(
        second["id"],
        datetime(2026, 2, 20, 9, 0, tzinfo=timezone.utc),
    )

    monthly = _report(
        client,
        admin_auth,
        date_from="2026-02-01",
        date_to="2026-02-28",
        group_by="month",
    )
    assert monthly["periods"] == [
        {
            "period": "2026-02",
            "delivered_orders": 2,
            "gross_revenue": first["total"] + second["total"],
            "refunded_total": 0,
            "net_revenue": first["total"] + second["total"],
        }
    ]

    daily = _report(
        client,
        admin_auth,
        date_from="2026-02-01",
        date_to="2026-02-28",
        group_by="day",
    )
    assert [item["period"] for item in daily["periods"]] == [
        "2026-02-10",
        "2026-02-20",
    ]
    assert [item["delivered_orders"] for item in daily["periods"]] == [
        1,
        1,
    ]
