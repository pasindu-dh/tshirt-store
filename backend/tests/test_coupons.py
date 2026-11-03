from datetime import datetime, timedelta, timezone


def _create_coupon(client, admin_headers, **overrides):
    payload = {
        "code": "SAVE10",
        "description": "10% off",
        "discount_type": "percent",
        "value": 10,
        "min_subtotal": 1000,
        "usage_limit": 5,
        "is_active": True,
    }
    payload.update(overrides)

    response = client.post(
        "/admin/coupons",
        headers=admin_headers,
        json=payload,
    )
    return response


def _add_product_to_cart(client, headers, product, quantity=2):
    variant = product["variants"][0]
    response = client.post(
        "/cart/items",
        headers=headers,
        json={"variant_id": variant["id"], "quantity": quantity},
    )
    assert response.status_code == 200, response.text


def test_admin_coupon_crud_and_permissions(client, admin_auth):
    created = _create_coupon(client, admin_auth["headers"])

    assert created.status_code == 201, created.text
    coupon = created.json()
    assert coupon["code"] == "SAVE10"
    assert coupon["used_count"] == 0

    duplicate = _create_coupon(client, admin_auth["headers"])
    assert duplicate.status_code == 409

    listing = client.get(
        "/admin/coupons", headers=admin_auth["headers"]
    )
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [coupon["id"]]

    updated = client.put(
        f"/admin/coupons/{coupon['id']}",
        headers=admin_auth["headers"],
        json={"value": 15, "description": "15% off"},
    )
    assert updated.status_code == 200
    assert updated.json()["value"] == 15

    invalid_percent = _create_coupon(
        client,
        admin_auth["headers"],
        code="TOOMUCH",
        value=101,
    )
    assert invalid_percent.status_code == 422

    deleted = client.delete(
        f"/admin/coupons/{coupon['id']}",
        headers=admin_auth["headers"],
    )
    assert deleted.status_code == 204
    assert (
        client.delete(
            f"/admin/coupons/{coupon['id']}",
            headers=admin_auth["headers"],
        ).status_code
        == 404
    )


def test_customer_cannot_manage_coupons(client, customer_auth):
    anonymous = client.get("/admin/coupons")
    customer = client.get(
        "/admin/coupons", headers=customer_auth["headers"]
    )

    assert anonymous.status_code == 401
    assert customer.status_code == 403


def test_coupon_preview_and_order_discount(
    client, admin_auth, customer_auth, product, order_payload
):
    headers = customer_auth["headers"]
    _add_product_to_cart(client, headers, product, 2)
    _create_coupon(client, admin_auth["headers"])

    preview = client.post(
        "/coupons/preview",
        headers=headers,
        json={"code": "save10"},
    )
    assert preview.status_code == 200, preview.text
    preview_data = preview.json()
    assert preview_data["subtotal"] == product["price"] * 2
    assert preview_data["discount_amount"] == (
        product["price"] * 2 * 10 // 100
    )
    assert preview_data["total"] == (
        product["price"] * 2
        - preview_data["discount_amount"]
        + 350
    )

    order = client.post(
        "/orders",
        headers=headers,
        json={**order_payload, "coupon_code": "save10"},
    )
    assert order.status_code == 201, order.text
    order_data = order.json()
    assert order_data["discount_code"] == "SAVE10"
    assert order_data["discount_amount"] == preview_data["discount_amount"]
    assert order_data["total"] == preview_data["total"]

    coupons = client.get(
        "/admin/coupons", headers=admin_auth["headers"]
    ).json()
    assert coupons[0]["used_count"] == 1


def test_coupon_preview_requires_auth_and_items(
    client, customer_auth, product, admin_auth
):
    anonymous = client.post(
        "/coupons/preview", json={"code": "SAVE10"}
    )
    assert anonymous.status_code == 401

    empty_cart = client.post(
        "/coupons/preview",
        headers=customer_auth["headers"],
        json={"code": "SAVE10"},
    )
    assert empty_cart.status_code == 400
    assert empty_cart.json()["detail"] == "Your cart is empty."

    _create_coupon(client, admin_auth["headers"])
    _add_product_to_cart(client, customer_auth["headers"], product, 1)

    unknown = client.post(
        "/coupons/preview",
        headers=customer_auth["headers"],
        json={"code": "NOPE"},
    )
    assert unknown.status_code == 400


def test_coupon_rules_and_usage_limit_restoration(
    client, admin_auth, customer_auth, product, order_payload
):
    headers = customer_auth["headers"]
    _create_coupon(
        client,
        admin_auth["headers"],
        code="ONCE",
        value=10,
        usage_limit=1,
        min_subtotal=1000,
    )

    _add_product_to_cart(client, headers, product, 1)
    first_order = client.post(
        "/orders",
        headers=headers,
        json={**order_payload, "coupon_code": "ONCE"},
    )
    assert first_order.status_code == 201

    _add_product_to_cart(client, headers, product, 1)
    exhausted_preview = client.post(
        "/coupons/preview",
        headers=headers,
        json={"code": "ONCE"},
    )
    assert exhausted_preview.status_code == 400
    assert "usage limit" in exhausted_preview.json()["detail"]

    exhausted_order = client.post(
        "/orders",
        headers=headers,
        json={**order_payload, "coupon_code": "ONCE"},
    )
    assert exhausted_order.status_code == 400

    cancelled = client.patch(
        f"/admin/orders/{first_order.json()['id']}/status",
        headers=admin_auth["headers"],
        json={"status": "cancelled"},
    )
    assert cancelled.status_code == 200

    allowed_again = client.post(
        "/coupons/preview",
        headers=headers,
        json={"code": "ONCE"},
    )
    assert allowed_again.status_code == 200


def test_coupon_minimum_expiry_fixed_discount_and_inactive(
    client, admin_auth, customer_auth, product
):
    headers = customer_auth["headers"]
    future = datetime.now(timezone.utc) + timedelta(days=2)
    past = datetime.now(timezone.utc) - timedelta(days=2)

    _create_coupon(
        client,
        admin_auth["headers"],
        code="FIXED",
        discount_type="fixed",
        value=200,
        min_subtotal=4000,
    )
    _create_coupon(
        client,
        admin_auth["headers"],
        code="FUTURE",
        starts_at=future.isoformat(),
    )
    _create_coupon(
        client,
        admin_auth["headers"],
        code="EXPIRED",
        expires_at=past.isoformat(),
    )
    _create_coupon(
        client,
        admin_auth["headers"],
        code="INACTIVE",
        is_active=False,
    )

    _add_product_to_cart(client, headers, product, 1)

    below_minimum = client.post(
        "/coupons/preview",
        headers=headers,
        json={"code": "FIXED"},
    )
    assert below_minimum.status_code == 400
    assert "Add LKR" in below_minimum.json()["detail"]

    not_started = client.post(
        "/coupons/preview",
        headers=headers,
        json={"code": "FUTURE"},
    )
    assert not_started.status_code == 400
    assert "not active yet" in not_started.json()["detail"]

    expired = client.post(
        "/coupons/preview",
        headers=headers,
        json={"code": "EXPIRED"},
    )
    assert expired.status_code == 400
    assert "expired" in expired.json()["detail"]

    inactive = client.post(
        "/coupons/preview",
        headers=headers,
        json={"code": "INACTIVE"},
    )
    assert inactive.status_code == 400
    assert "not active" in inactive.json()["detail"]
