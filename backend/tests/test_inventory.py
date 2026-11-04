from datetime import datetime, timezone


def _add_to_cart(client, headers, variant_id, quantity=1):
    response = client.post(
        "/cart/items",
        headers=headers,
        json={"variant_id": variant_id, "quantity": quantity},
    )
    assert response.status_code == 200, response.text


def _create_cod_order(
    client,
    customer_auth,
    product,
    order_payload,
    *,
    quantity=1,
    variant=None,
):
    variant = variant or product["variants"][0]
    _add_to_cart(
        client,
        customer_auth["headers"],
        variant["id"],
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


def _movements(client, admin_auth, **params):
    response = client.get(
        "/admin/inventory/movements",
        headers=admin_auth["headers"],
        params={"limit": 100, **params},
    )
    assert response.status_code == 200, response.text
    return response.json(), int(
        response.headers["X-Total-Count"]
    )


def _variant_by_size(product, size):
    return next(
        variant
        for variant in product["variants"]
        if variant["size"] == size
    )


def test_order_cancellation_and_return_stock_movements(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
):
    variant = _variant_by_size(product, "M")
    order = _create_cod_order(
        client,
        customer_auth,
        product,
        order_payload,
        quantity=2,
    )
    admin_id = admin_auth["user"]["id"]

    movements, total = _movements(
        client, admin_auth, variant_id=variant["id"]
    )
    initial = next(
        item
        for item in movements
        if item["movement_type"] == "initial_stock"
    )
    placed = next(
        item
        for item in movements
        if item["movement_type"] == "order_placed"
    )
    assert initial["quantity_delta"] == 8
    assert initial["stock_before"] == 0
    assert initial["stock_after"] == 8
    assert initial["actor_user_id"] == admin_id

    assert placed["quantity_delta"] == -2
    assert placed["stock_before"] == 8
    assert placed["stock_after"] == 6
    assert placed["order_id"] == order["id"]
    assert placed["product_name"] == product["name"]
    assert placed["sku"] == variant["sku"]
    assert total >= 2

    cancelled = client.patch(
        f"/admin/orders/{order['id']}/status",
        headers=admin_auth["headers"],
        json={"status": "cancelled"},
    )
    assert cancelled.status_code == 200

    movements, _ = _movements(
        client, admin_auth, variant_id=variant["id"]
    )
    released = next(
        item
        for item in movements
        if item["movement_type"] == "order_cancelled"
    )
    assert released["quantity_delta"] == 2
    assert released["stock_before"] == 6
    assert released["stock_after"] == 8
    assert released["order_id"] == order["id"]
    assert released["actor_user_id"] == admin_id

    second = _create_cod_order(
        client, customer_auth, product, order_payload
    )
    _deliver_order(client, admin_auth, second)
    request = client.post(
        f"/orders/{second['id']}/returns",
        headers=customer_auth["headers"],
        json={
            "reason": "Inventory movement test.",
            "items": [
                {
                    "order_item_id": second["items"][0]["id"],
                    "quantity": 1,
                }
            ],
        },
    )
    assert request.status_code == 201, request.text
    request_id = request.json()["id"]

    approved = client.patch(
        f"/admin/orders/{second['id']}/returns/{request_id}",
        headers=admin_auth["headers"],
        json={"status": "approved"},
    )
    completed = client.patch(
        f"/admin/orders/{second['id']}/returns/{request_id}",
        headers=admin_auth["headers"],
        json={"status": "completed"},
    )
    assert approved.status_code == 200
    assert completed.status_code == 200

    movements, _ = _movements(
        client, admin_auth, variant_id=variant["id"]
    )
    restocked = next(
        item
        for item in movements
        if item["movement_type"] == "return_restocked"
    )
    assert restocked["quantity_delta"] == 1
    assert restocked["stock_before"] == 7
    assert restocked["stock_after"] == 8
    assert restocked["order_id"] == second["id"]
    assert restocked["return_request_id"] == request_id
    assert restocked["actor_user_id"] == admin_id


def test_manual_adjustment_thresholds_and_variant_identity(
    client,
    admin_auth,
    customer_auth,
    create_product,
):
    product = create_product(
        variants=[
            {
                "size": "M",
                "color": "Black",
                "sku": "INV-M",
                "stock": 4,
                "low_stock_threshold": 3,
            },
            {
                "size": "L",
                "color": "Black",
                "sku": "INV-L",
                "stock": 6,
                "low_stock_threshold": 10,
            },
            {
                "size": "XL",
                "color": "Black",
                "sku": "INV-XL",
                "stock": 0,
                "low_stock_threshold": 0,
            },
        ]
    )
    medium = _variant_by_size(product, "M")
    large = _variant_by_size(product, "L")
    extra_large = _variant_by_size(product, "XL")

    low_stock = client.get(
        "/admin/inventory/low-stock",
        headers=admin_auth["headers"],
    )
    assert low_stock.status_code == 200
    assert low_stock.headers["X-Total-Count"] == "2"
    assert {item["id"] for item in low_stock.json()} == {
        large["id"],
        extra_large["id"],
    }
    assert {
        item["low_stock_threshold"]
        for item in low_stock.json()
    } == {0, 10}

    adjusted = client.post(
        f"/admin/inventory/variants/{medium['id']}/adjust",
        headers=admin_auth["headers"],
        json={
            "quantity_delta": -2,
            "reason": "Cycle count correction.",
        },
    )
    assert adjusted.status_code == 200, adjusted.text
    result = adjusted.json()
    assert result["variant"]["id"] == medium["id"]
    assert result["variant"]["stock"] == 2
    assert result["variant"]["low_stock_threshold"] == 3
    assert result["movement"]["movement_type"] == (
        "manual_adjustment"
    )
    assert result["movement"]["quantity_delta"] == -2
    assert result["movement"]["stock_before"] == 4
    assert result["movement"]["stock_after"] == 2
    assert result["movement"]["reason"] == (
        "Cycle count correction."
    )
    assert result["movement"]["actor_user_id"] == (
        admin_auth["user"]["id"]
    )

    after_adjustment = client.get(
        "/admin/inventory/low-stock",
        headers=admin_auth["headers"],
    )
    assert after_adjustment.headers["X-Total-Count"] == "3"

    too_much = client.post(
        f"/admin/inventory/variants/{medium['id']}/adjust",
        headers=admin_auth["headers"],
        json={
            "quantity_delta": -3,
            "reason": "Cannot remove more than stock.",
        },
    )
    assert too_much.status_code == 400
    zero = client.post(
        f"/admin/inventory/variants/{medium['id']}/adjust",
        headers=admin_auth["headers"],
        json={
            "quantity_delta": 0,
            "reason": "No-op adjustment.",
        },
    )
    blank_reason = client.post(
        f"/admin/inventory/variants/{medium['id']}/adjust",
        headers=admin_auth["headers"],
        json={
            "quantity_delta": 1,
            "reason": "   ",
        },
    )
    assert zero.status_code == 422
    assert blank_reason.status_code == 422
    customer = client.post(
        f"/admin/inventory/variants/{medium['id']}/adjust",
        headers=customer_auth["headers"],
        json={
            "quantity_delta": 1,
            "reason": "Customer cannot adjust.",
        },
    )
    anonymous = client.post(
        f"/admin/inventory/variants/{medium['id']}/adjust",
        json={
            "quantity_delta": 1,
            "reason": "Anonymous cannot adjust.",
        },
    )
    assert customer.status_code == 403
    assert anonymous.status_code == 401

    variants_payload = [
        {
            "size": variant["size"],
            "color": variant["color"],
            "sku": variant["sku"],
            "stock": 5 if variant["size"] == "M" else variant["stock"],
            "low_stock_threshold": (
                0
                if variant["size"] == "M"
                else variant["low_stock_threshold"]
            ),
        }
        for variant in product["variants"]
    ]
    updated = client.put(
        f"/admin/products/{product['id']}",
        headers=admin_auth["headers"],
        json={"variants": variants_payload},
    )
    assert updated.status_code == 200, updated.text
    updated_medium = _variant_by_size(updated.json(), "M")
    assert updated_medium["id"] == medium["id"]
    assert updated_medium["stock"] == 5
    assert updated_medium["low_stock_threshold"] == 0

    movements, _ = _movements(
        client,
        admin_auth,
        variant_id=medium["id"],
        movement_type="manual_adjustment",
    )
    latest = movements[0]
    assert latest["quantity_delta"] == 3
    assert latest["stock_before"] == 2
    assert latest["stock_after"] == 5

    low_stock_after_update = client.get(
        "/admin/inventory/low-stock",
        headers=admin_auth["headers"],
    )
    assert low_stock_after_update.headers["X-Total-Count"] == "2"

    stats = client.get(
        "/admin/stats", headers=admin_auth["headers"]
    ).json()
    assert stats["low_stock_variants"] == 2
    assert stats["out_of_stock_variants"] == 1

    deactivated = client.put(
        f"/admin/products/{product['id']}",
        headers=admin_auth["headers"],
        json={"is_active": False},
    )
    assert deactivated.status_code == 200

    empty_low_stock = client.get(
        "/admin/inventory/low-stock",
        headers=admin_auth["headers"],
    )
    assert empty_low_stock.headers["X-Total-Count"] == "0"
    stats = client.get(
        "/admin/stats", headers=admin_auth["headers"]
    ).json()
    assert stats["low_stock_variants"] == 0
    assert stats["out_of_stock_variants"] == 0


def test_stock_movement_filters_and_product_deletion_snapshots(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
):
    variant = _variant_by_size(product, "M")
    _create_cod_order(
        client, customer_auth, product, order_payload
    )

    only_orders, total = _movements(
        client, admin_auth, movement_type="order_placed"
    )
    assert total == 1
    assert only_orders[0]["movement_type"] == "order_placed"

    no_matches, total = _movements(
        client, admin_auth, search="does-not-exist"
    )
    assert no_matches == []
    assert total == 0

    variant_movements, total = _movements(
        client, admin_auth, variant_id=variant["id"]
    )
    assert total >= 2
    assert all(
        item["variant_id"] == variant["id"]
        for item in variant_movements
    )

    today = datetime.now(timezone.utc).date().isoformat()
    dated, total = _movements(
        client,
        admin_auth,
        date_from=today,
        date_to=today,
    )
    assert total >= 2
    assert dated

    invalid_range = client.get(
        "/admin/inventory/movements",
        headers=admin_auth["headers"],
        params={
            "date_from": "2026-02-01",
            "date_to": "2026-01-01",
        },
    )
    assert invalid_range.status_code == 400

    invalid_type = client.get(
        "/admin/inventory/movements",
        headers=admin_auth["headers"],
        params={"movement_type": "not-a-type"},
    )
    assert invalid_type.status_code == 422

    customer_access = client.get(
        "/admin/inventory/movements",
        headers=customer_auth["headers"],
    )
    anonymous_access = client.get(
        "/admin/inventory/movements"
    )
    customer_low_stock = client.get(
        "/admin/inventory/low-stock",
        headers=customer_auth["headers"],
    )
    assert customer_access.status_code == 403
    assert anonymous_access.status_code == 401
    assert customer_low_stock.status_code == 403

    deleted = client.delete(
        f"/admin/products/{product['id']}",
        headers=admin_auth["headers"],
    )
    assert deleted.status_code == 204

    movements, total = _movements(
        client, admin_auth, search=product["name"]
    )
    deletion_movements = [
        item
        for item in movements
        if item["movement_type"] == "product_deleted"
    ]
    assert len(deletion_movements) == 2
    assert {item["sku"] for item in deletion_movements} == {
        variant["sku"],
        _variant_by_size(product, "L")["sku"],
    }
    assert all(
        item["quantity_delta"] < 0
        and item["stock_after"] == 0
        and item["variant_id"] is None
        and item["product_id"] is None
        for item in deletion_movements
    )
    assert total >= 2
