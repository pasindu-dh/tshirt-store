def _create_method(
    client,
    admin_auth,
    *,
    name,
    fee,
    is_active=True,
    sort_order=0,
    description="",
):
    return client.post(
        "/admin/shipping-methods",
        headers=admin_auth["headers"],
        json={
            "name": name,
            "description": description,
            "fee_lkr": fee,
            "is_active": is_active,
            "sort_order": sort_order,
        },
    )


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
    shipping_method_id=None,
):
    _add_to_cart(
        client, customer_auth["headers"], product, 1
    )
    payload = {**order_payload}

    if shipping_method_id is not None:
        payload["shipping_method_id"] = shipping_method_id

    response = client.post(
        "/orders",
        headers=customer_auth["headers"],
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_shipping_method_admin_crud_and_public_list(
    client,
    admin_auth,
    customer_auth,
):
    empty = client.get("/shipping-methods")
    assert empty.status_code == 200
    assert empty.json() == []

    standard = _create_method(
        client,
        admin_auth,
        name="Standard Delivery",
        fee=350,
    )
    express = _create_method(
        client,
        admin_auth,
        name="Express Delivery",
        fee=900,
        sort_order=1,
    )
    pickup = _create_method(
        client,
        admin_auth,
        name="Store Pickup",
        fee=0,
        is_active=False,
        sort_order=2,
    )
    assert standard.status_code == 201
    assert express.status_code == 201
    assert pickup.status_code == 201
    standard_id = standard.json()["id"]
    express_id = express.json()["id"]

    public = client.get("/shipping-methods")
    assert public.status_code == 200
    assert [item["name"] for item in public.json()] == [
        "Standard Delivery",
        "Express Delivery",
    ]
    assert [item["fee_lkr"] for item in public.json()] == [
        350,
        900,
    ]

    admin_list = client.get(
        "/admin/shipping-methods",
        headers=admin_auth["headers"],
    )
    assert admin_list.status_code == 200
    assert len(admin_list.json()) == 3

    updated = client.patch(
        f"/admin/shipping-methods/{express_id}",
        headers=admin_auth["headers"],
        json={
            "name": "Express Plus",
            "fee_lkr": 1000,
            "description": "Next-day delivery.",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Express Plus"
    assert updated.json()["fee_lkr"] == 1000

    deactivated = client.patch(
        f"/admin/shipping-methods/{express_id}",
        headers=admin_auth["headers"],
        json={"is_active": False},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    public = client.get("/shipping-methods").json()
    assert [item["id"] for item in public] == [standard_id]

    duplicate = _create_method(
        client,
        admin_auth,
        name="Standard Delivery",
        fee=400,
    )
    invalid_fee = _create_method(
        client,
        admin_auth,
        name="Free Delivery",
        fee=-1,
    )
    blank_name = _create_method(
        client,
        admin_auth,
        name="   ",
        fee=100,
    )
    empty_update = client.patch(
        f"/admin/shipping-methods/{express_id}",
        headers=admin_auth["headers"],
        json={},
    )
    assert duplicate.status_code == 409
    assert invalid_fee.status_code == 422
    assert blank_name.status_code == 422
    assert empty_update.status_code == 422

    deleted = client.delete(
        f"/admin/shipping-methods/{express_id}",
        headers=admin_auth["headers"],
    )
    missing = client.patch(
        "/admin/shipping-methods/999999",
        headers=admin_auth["headers"],
        json={"fee_lkr": 100},
    )
    customer_admin = client.get(
        "/admin/shipping-methods",
        headers=customer_auth["headers"],
    )
    anonymous_admin = client.get(
        "/admin/shipping-methods"
    )
    assert deleted.status_code == 204
    assert missing.status_code == 404
    assert customer_admin.status_code == 403
    assert anonymous_admin.status_code == 401


def test_order_uses_selected_shipping_method_and_snapshots_it(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
):
    standard = _create_method(
        client,
        admin_auth,
        name="Standard Delivery",
        fee=350,
    ).json()
    express = _create_method(
        client,
        admin_auth,
        name="Express Delivery",
        fee=900,
        sort_order=1,
    ).json()
    _create_method(
        client,
        admin_auth,
        name="Inactive Delivery",
        fee=50,
        is_active=False,
    )

    _add_to_cart(
        client, customer_auth["headers"], product, 1
    )
    cart = client.get(
        "/cart", headers=customer_auth["headers"]
    ).json()
    assert cart["shipping_fee"] == 350
    client.delete(
        "/cart", headers=customer_auth["headers"]
    )

    express_order = _create_order(
        client,
        customer_auth,
        product,
        order_payload,
        shipping_method_id=express["id"],
    )
    assert express_order["shipping_method_id"] == express["id"]
    assert (
        express_order["shipping_method_name"]
        == "Express Delivery"
    )
    assert express_order["shipping_fee"] == 900
    assert express_order["total"] == (
        express_order["subtotal"]
        - express_order["discount_amount"]
        + 900
    )

    default_order = _create_order(
        client, customer_auth, product, order_payload
    )
    assert default_order["shipping_method_id"] == standard["id"]
    assert (
        default_order["shipping_method_name"]
        == "Standard Delivery"
    )
    assert default_order["shipping_fee"] == 350

    inactive = _create_method(
        client,
        admin_auth,
        name="Disabled Delivery",
        fee=10,
        is_active=False,
    ).json()
    _add_to_cart(
        client, customer_auth["headers"], product, 1
    )
    unavailable = client.post(
        "/orders",
        headers=customer_auth["headers"],
        json={
            **order_payload,
            "shipping_method_id": inactive["id"],
        },
    )
    missing = client.post(
        "/orders",
        headers=customer_auth["headers"],
        json={
            **order_payload,
            "shipping_method_id": 999999,
        },
    )
    assert unavailable.status_code == 400
    assert missing.status_code == 400
    assert "shipping method" in unavailable.json()["detail"].lower()
    assert "shipping method" in missing.json()["detail"].lower()

    fetched = client.get(
        f"/orders/{express_order['id']}",
        headers=customer_auth["headers"],
    ).json()
    assert fetched["shipping_method_name"] == "Express Delivery"
    assert fetched["shipping_fee"] == 900


def test_order_falls_back_to_flat_fee_without_methods(
    client,
    customer_auth,
    product,
    order_payload,
):
    order = _create_order(
        client, customer_auth, product, order_payload
    )

    assert order["shipping_method_id"] is None
    assert order["shipping_method_name"] == "Standard Delivery"
    assert order["shipping_fee"] == 350
