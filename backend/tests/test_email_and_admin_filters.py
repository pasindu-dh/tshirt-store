from datetime import datetime, timedelta, timezone


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
    to_email, order_id, contact_name, total = calls[0]
    assert to_email == customer_auth["user"]["email"]
    assert order_id == response.json()["id"]
    assert contact_name == order_payload["contact_name"]
    assert total == response.json()["total"]


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
