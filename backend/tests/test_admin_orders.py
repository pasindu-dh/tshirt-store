def _place_order(client, headers, order_payload, product, quantity=2):
    variant_m = next(
        variant for variant in product["variants"] if variant["size"] == "M"
    )
    added = client.post(
        "/cart/items",
        headers=headers,
        json={"variant_id": variant_m["id"], "quantity": quantity},
    )
    assert added.status_code == 200, added.text

    response = client.post(
        "/orders", headers=headers, json=order_payload
    )
    assert response.status_code == 201, response.text
    return response.json(), variant_m


def _set_status(client, headers, order_id, status):
    return client.patch(
        f"/admin/orders/{order_id}/status",
        headers=headers,
        json={"status": status},
    )


def test_admin_order_lifecycle_filters_and_stats(
    client, admin_auth, customer_auth, product, order_payload
):
    admin_headers = admin_auth["headers"]
    order, _ = _place_order(
        client, customer_auth["headers"], order_payload, product
    )

    listing = client.get("/admin/orders", headers=admin_headers)
    assert listing.status_code == 200
    assert listing.headers["X-Total-Count"] == "1"
    assert [item["id"] for item in listing.json()] == [order["id"]]

    by_id = client.get(
        "/admin/orders",
        headers=admin_headers,
        params={"search": str(order["id"])},
    )
    assert by_id.headers["X-Total-Count"] == "1"
    assert [item["id"] for item in by_id.json()] == [order["id"]]

    by_name = client.get(
        "/admin/orders",
        headers=admin_headers,
        params={"search": "Test Customer"},
    )
    assert by_name.headers["X-Total-Count"] == "1"

    pending_only = client.get(
        "/admin/orders",
        headers=admin_headers,
        params={"status": "pending"},
    )
    confirmed_only = client.get(
        "/admin/orders",
        headers=admin_headers,
        params={"status": "confirmed"},
    )
    assert pending_only.headers["X-Total-Count"] == "1"
    assert confirmed_only.headers["X-Total-Count"] == "0"

    invalid_transition = _set_status(
        client, admin_headers, order["id"], "shipped"
    )
    assert invalid_transition.status_code == 409

    same_status = _set_status(
        client, admin_headers, order["id"], "pending"
    )
    assert same_status.status_code == 409

    confirmed = _set_status(
        client, admin_headers, order["id"], "confirmed"
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"

    shipped = _set_status(client, admin_headers, order["id"], "shipped")
    assert shipped.status_code == 200
    assert shipped.json()["status"] == "shipped"

    delivered = _set_status(
        client, admin_headers, order["id"], "delivered"
    )
    assert delivered.status_code == 200
    assert delivered.json()["status"] == "delivered"
    assert delivered.json()["payment_status"] == "paid"

    terminal = _set_status(
        client, admin_headers, order["id"], "cancelled"
    )
    assert terminal.status_code == 409

    detail = client.get(
        f"/admin/orders/{order['id']}", headers=admin_headers
    )
    assert detail.status_code == 200
    assert detail.json()["items"]

    stats = client.get("/admin/stats", headers=admin_headers)
    assert stats.status_code == 200
    stats_data = stats.json()
    assert stats_data["orders_total"] == 1
    assert stats_data["delivered_orders"] == 1
    assert stats_data["open_orders"] == 0
    assert stats_data["revenue"] == order["total"]

    customer_list = client.get(
        "/admin/orders", headers=customer_auth["headers"]
    )
    assert customer_list.status_code == 403


def test_cancellation_restores_stock(
    client, admin_auth, customer_auth, product, order_payload
):
    admin_headers = admin_auth["headers"]
    order, variant_m = _place_order(
        client,
        customer_auth["headers"],
        order_payload,
        product,
        quantity=3,
    )

    after_order = client.get(
        f"/admin/products/{product['id']}", headers=admin_headers
    )
    stock_after_order = next(
        variant["stock"]
        for variant in after_order.json()["variants"]
        if variant["id"] == variant_m["id"]
    )
    assert stock_after_order == 5

    cancelled = _set_status(
        client, admin_headers, order["id"], "cancelled"
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["payment_status"] == "cancelled"

    after_cancel = client.get(
        f"/admin/products/{product['id']}", headers=admin_headers
    )
    stock_after_cancel = next(
        variant["stock"]
        for variant in after_cancel.json()["variants"]
        if variant["id"] == variant_m["id"]
    )
    assert stock_after_cancel == 8

    stats = client.get("/admin/stats", headers=admin_headers).json()
    assert stats["cancelled_orders"] == 1
    assert stats["open_orders"] == 0
    assert stats["revenue"] == 0


def test_order_search_is_exact_for_numeric_terms(
    client, admin_auth, customer_auth, product, order_payload
):
    headers = customer_auth["headers"]
    first, _ = _place_order(client, headers, order_payload, product, 1)
    second, _ = _place_order(client, headers, order_payload, product, 1)

    admin_headers = admin_auth["headers"]
    by_id = client.get(
        "/admin/orders",
        headers=admin_headers,
        params={"search": str(first["id"])},
    )
    assert by_id.headers["X-Total-Count"] == "1"
    assert [item["id"] for item in by_id.json()] == [first["id"]]

    by_email = client.get(
        "/admin/orders",
        headers=admin_headers,
        params={"search": customer_auth["user"]["email"]},
    )
    assert by_email.headers["X-Total-Count"] == "2"
    assert {item["id"] for item in by_email.json()} == {
        first["id"],
        second["id"],
    }
