from datetime import datetime, timedelta, timezone

from app.services.email import send_order_confirmation


def _add_product_to_cart(client, headers, product, quantity=1):
    variant = product["variants"][0]
    response = client.post(
        "/cart/items",
        headers=headers,
        json={"variant_id": variant["id"], "quantity": quantity},
    )
    assert response.status_code == 200, response.text


def test_order_confirmation_email_is_scheduled(
    client, customer_auth, product, order_payload, monkeypatch
):
    calls = []
    monkeypatch.setattr(
        "app.routers.orders.send_order_confirmation",
        lambda *args: calls.append(args),
    )

    _add_product_to_cart(
        client, customer_auth["headers"], product, 1
    )
    response = client.post(
        "/orders",
        headers=customer_auth["headers"],
        json=order_payload,
    )
    assert response.status_code == 201

    assert len(calls) == 1
    (
        to_email,
        order_id,
        contact_name,
        total,
        payment_method,
        payment_status,
    ) = calls[0]
    assert to_email == customer_auth["user"]["email"]
    assert order_id == response.json()["id"]
    assert contact_name == order_payload["contact_name"]
    assert total == response.json()["total"]
    assert payment_method == "cod"
    assert payment_status == "pending"


def test_status_update_email_is_scheduled(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
    monkeypatch,
):
    calls = []
    monkeypatch.setattr(
        "app.routers.admin_orders.send_order_status_update",
        lambda *args: calls.append(args),
    )

    _add_product_to_cart(
        client, customer_auth["headers"], product, 1
    )
    order = client.post(
        "/orders",
        headers=customer_auth["headers"],
        json=order_payload,
    )
    assert order.status_code == 201

    updated = client.patch(
        f"/admin/orders/{order.json()['id']}/status",
        headers=admin_auth["headers"],
        json={"status": "confirmed"},
    )
    assert updated.status_code == 200

    assert calls == [
        (
            customer_auth["user"]["email"],
            order.json()["id"],
            "confirmed",
        )
    ]


def test_admin_order_date_filters(
    client, admin_auth, customer_auth, product, order_payload
):
    _add_product_to_cart(
        client, customer_auth["headers"], product, 1
    )
    order = client.post(
        "/orders",
        headers=customer_auth["headers"],
        json=order_payload,
    )
    assert order.status_code == 201

    today = datetime.now(timezone.utc).date()
    tomorrow = today + timedelta(days=1)
    yesterday = today - timedelta(days=1)

    same_day = client.get(
        "/admin/orders",
        headers=admin_auth["headers"],
        params={
            "date_from": today.isoformat(),
            "date_to": today.isoformat(),
        },
    )
    assert same_day.status_code == 200
    assert same_day.headers["X-Total-Count"] == "1"

    future = client.get(
        "/admin/orders",
        headers=admin_auth["headers"],
        params={"date_from": tomorrow.isoformat()},
    )
    assert future.headers["X-Total-Count"] == "0"

    past_only = client.get(
        "/admin/orders",
        headers=admin_auth["headers"],
        params={"date_to": yesterday.isoformat()},
    )
    assert past_only.headers["X-Total-Count"] == "0"

    invalid = client.get(
        "/admin/orders",
        headers=admin_auth["headers"],
        params={"date_from": "not-a-date"},
    )
    assert invalid.status_code == 422


def test_order_confirmation_wording_distinguishes_pending_payment(
    monkeypatch,
):
    calls = []
    monkeypatch.setattr(
        "app.services.email._send_email",
        lambda to_email, subject, body: calls.append(
            (subject, body)
        )
        or True,
    )

    send_order_confirmation(
        "customer@furzy.dev",
        7,
        "Customer",
        2850,
        "online",
        "pending",
    )
    assert "payment pending" in calls[0][0].lower()
    assert "has not been confirmed" in calls[0][1]

    calls.clear()
    send_order_confirmation(
        "customer@furzy.dev",
        8,
        "Customer",
        2500,
        "cod",
        "pending",
    )
    assert "confirmed" in calls[0][0].lower()
    assert "Cash on Delivery" in calls[0][1]
    assert "not been confirmed" not in calls[0][1]


def test_payment_confirmation_only_after_verified_payment(
    client, customer_auth, product, order_payload, monkeypatch
):
    calls = []
    monkeypatch.setattr(
        "app.routers.payments.send_payment_confirmation",
        lambda *args: calls.append(args),
    )

    _add_product_to_cart(
        client, customer_auth["headers"], product, 1
    )
    order = client.post(
        "/orders",
        headers=customer_auth["headers"],
        json={**order_payload, "payment_method": "online"},
    )
    assert order.status_code == 201
    assert calls == []

    session = client.post(
        f"/payments/orders/{order.json()['id']}/session",
        headers=customer_auth["headers"],
    )
    assert session.status_code == 200
    assert calls == []

    completed = client.post(
        f"/payments/orders/{order.json()['id']}/mock-complete",
        headers=customer_auth["headers"],
    )
    assert completed.status_code == 200
    assert len(calls) == 1
    assert calls[0][0] == customer_auth["user"]["email"]
    assert calls[0][1] == order.json()["id"]
    assert calls[0][4] == session.json()["reference"]

    duplicate = client.post(
        f"/payments/orders/{order.json()['id']}/mock-complete",
        headers=customer_auth["headers"],
    )
    assert duplicate.status_code == 200
    assert len(calls) == 1
