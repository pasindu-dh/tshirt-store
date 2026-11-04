def _add_to_cart(client, headers, product, quantity):
    response = client.post(
        "/cart/items",
        headers=headers,
        json={
            "variant_id": product["variants"][0]["id"],
            "quantity": quantity,
        },
    )
    assert response.status_code == 200, response.text


def _place_order(
    client,
    customer_auth,
    product,
    order_payload,
    quantity=1,
):
    _add_to_cart(
        client, customer_auth["headers"], product, quantity
    )
    response = client.post(
        "/orders",
        headers=customer_auth["headers"],
        json=order_payload,
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


def _list_notifications(client, admin_auth, **params):
    response = client.get(
        "/admin/notifications",
        headers=admin_auth["headers"],
        params={"limit": 100, **params},
    )
    assert response.status_code == 200, response.text
    return response.json(), int(
        response.headers["X-Total-Count"]
    )


def _unread_count(client, admin_auth):
    response = client.get(
        "/admin/notifications/unread-count",
        headers=admin_auth["headers"],
    )
    assert response.status_code == 200
    return response.json()["count"]


def test_order_and_low_stock_notifications(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
):
    first = _place_order(
        client,
        customer_auth,
        product,
        order_payload,
        quantity=4,
    )
    notifications, total = _list_notifications(
        client, admin_auth
    )
    assert total == 2
    types = [item["notification_type"] for item in notifications]
    assert types.count("new_order") == 1
    assert types.count("low_stock") == 1

    order_notification = next(
        item
        for item in notifications
        if item["notification_type"] == "new_order"
    )
    assert order_notification["title"] == (
        f"New order #{first['id']}"
    )
    assert order_notification["link"] == (
        f"/admin/orders/{first['id']}"
    )
    assert order_notification["is_read"] is False

    low_stock = next(
        item
        for item in notifications
        if item["notification_type"] == "low_stock"
    )
    assert "has 4 left" in low_stock["message"]
    assert low_stock["link"] == "/admin/inventory"
    assert _unread_count(client, admin_auth) == 2

    second = _place_order(
        client,
        customer_auth,
        product,
        order_payload,
        quantity=1,
    )
    notifications, total = _list_notifications(
        client, admin_auth
    )
    assert total == 3
    assert (
        sum(
            1
            for item in notifications
            if item["notification_type"] == "low_stock"
        )
        == 1
    )
    assert any(
        item["link"] == f"/admin/orders/{second['id']}"
        for item in notifications
    )
    assert _unread_count(client, admin_auth) == 3

    marked = client.patch(
        f"/admin/notifications/{low_stock['id']}/read",
        headers=admin_auth["headers"],
    )
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True
    assert marked.json()["read_at"] is not None
    assert _unread_count(client, admin_auth) == 2

    mark_all = client.post(
        "/admin/notifications/read-all",
        headers=admin_auth["headers"],
    )
    assert mark_all.status_code == 200
    assert mark_all.json()["updated"] == 2
    assert _unread_count(client, admin_auth) == 0

    unread, unread_total = _list_notifications(
        client, admin_auth, unread_only=True
    )
    assert unread == []
    assert unread_total == 0

    customer_access = client.get(
        "/admin/notifications",
        headers=customer_auth["headers"],
    )
    anonymous_access = client.get(
        "/admin/notifications"
    )
    assert customer_access.status_code == 403
    assert anonymous_access.status_code == 401


def test_return_request_notification(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
):
    order = _place_order(
        client, customer_auth, product, order_payload
    )
    _deliver_order(client, admin_auth, order)
    response = client.post(
        f"/orders/{order['id']}/returns",
        headers=customer_auth["headers"],
        json={
            "reason_code": "damaged",
            "reason": "Arrived damaged.",
            "items": [
                {
                    "order_item_id": order["items"][0]["id"],
                    "quantity": 1,
                }
            ],
        },
    )
    assert response.status_code == 201, response.text
    return_id = response.json()["id"]

    notifications, total = _list_notifications(
        client, admin_auth
    )
    matches = [
        item
        for item in notifications
        if item["notification_type"] == "new_return"
    ]
    assert len(matches) == 1
    assert matches[0]["title"] == (
        f"New return request #{return_id}"
    )
    assert matches[0]["link"] == "/admin/returns"
    assert f"order #{order['id']}" in matches[0]["message"]
    assert total >= 2


def test_manual_adjustment_rearms_low_stock_alert(
    client,
    admin_auth,
    product,
):
    variant = product["variants"][0]

    first = client.post(
        f"/admin/inventory/variants/{variant['id']}/adjust",
        headers=admin_auth["headers"],
        json={
            "quantity_delta": -4,
            "reason": "Stocktake correction.",
        },
    )
    assert first.status_code == 200, first.text

    second = client.post(
        f"/admin/inventory/variants/{variant['id']}/adjust",
        headers=admin_auth["headers"],
        json={
            "quantity_delta": -1,
            "reason": "Further stocktake correction.",
        },
    )
    assert second.status_code == 200

    notifications, _ = _list_notifications(
        client, admin_auth
    )
    low_stock = [
        item
        for item in notifications
        if item["notification_type"] == "low_stock"
    ]
    assert len(low_stock) == 1

    restocked = client.post(
        f"/admin/inventory/variants/{variant['id']}/adjust",
        headers=admin_auth["headers"],
        json={
            "quantity_delta": 3,
            "reason": "Restock delivery.",
        },
    )
    assert restocked.status_code == 200
    crossed_again = client.post(
        f"/admin/inventory/variants/{variant['id']}/adjust",
        headers=admin_auth["headers"],
        json={
            "quantity_delta": -2,
            "reason": "Damaged units removed.",
        },
    )
    assert crossed_again.status_code == 200

    notifications, _ = _list_notifications(
        client, admin_auth
    )
    low_stock = [
        item
        for item in notifications
        if item["notification_type"] == "low_stock"
    ]
    assert len(low_stock) == 2
