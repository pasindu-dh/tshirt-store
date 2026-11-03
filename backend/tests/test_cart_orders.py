from app.database import SessionLocal
from app.models import ProductVariant


def _add_to_cart(client, headers, variant_id, quantity):
    return client.post(
        "/cart/items",
        headers=headers,
        json={"variant_id": variant_id, "quantity": quantity},
    )


def test_cart_operations_and_stock_caps(client, customer_auth, product):
    headers = customer_auth["headers"]
    variant_m = next(
        variant for variant in product["variants"] if variant["size"] == "M"
    )
    variant_l = next(
        variant for variant in product["variants"] if variant["size"] == "L"
    )
    price = product["price"]

    added = _add_to_cart(client, headers, variant_m["id"], 3)
    assert added.status_code == 200, added.text
    cart = added.json()
    assert cart["item_count"] == 3
    assert cart["subtotal"] == price * 3
    assert cart["shipping_fee"] == 350
    assert cart["total"] == price * 3 + 350

    added_again = _add_to_cart(client, headers, variant_m["id"], 2)
    assert added_again.status_code == 200
    cart = added_again.json()
    assert cart["item_count"] == 5
    assert len(cart["items"]) == 1
    assert cart["items"][0]["quantity"] == 5

    too_many = _add_to_cart(client, headers, variant_l["id"], 3)
    assert too_many.status_code == 409
    assert "Only 2" in too_many.json()["detail"]

    added_l = _add_to_cart(client, headers, variant_l["id"], 2)
    assert added_l.status_code == 200
    cart = added_l.json()
    assert cart["item_count"] == 7
    assert len(cart["items"]) == 2

    item_m = next(
        item
        for item in cart["items"]
        if item["variant_id"] == variant_m["id"]
    )
    over_stock = client.put(
        f"/cart/items/{item_m['id']}",
        headers=headers,
        json={"quantity": 99},
    )
    assert over_stock.status_code == 409

    updated = client.put(
        f"/cart/items/{item_m['id']}",
        headers=headers,
        json={"quantity": 1},
    )
    assert updated.status_code == 200
    assert updated.json()["item_count"] == 3

    removed = client.delete(
        f"/cart/items/{item_m['id']}", headers=headers
    )
    assert removed.status_code == 200
    assert removed.json()["item_count"] == 2

    cleared = client.delete("/cart", headers=headers)
    assert cleared.status_code == 200
    assert cleared.json()["items"] == []
    assert cleared.json()["subtotal"] == 0
    assert cleared.json()["shipping_fee"] == 0
    assert cleared.json()["total"] == 0


def test_cart_merge_caps_to_stock_and_skips_unknown(
    client, customer_auth, product
):
    headers = customer_auth["headers"]
    variant_m = next(
        variant for variant in product["variants"] if variant["size"] == "M"
    )
    variant_l = next(
        variant for variant in product["variants"] if variant["size"] == "L"
    )

    assert _add_to_cart(client, headers, variant_m["id"], 1).status_code == 200

    merged = client.post(
        "/cart/merge",
        headers=headers,
        json={
            "items": [
                {"variant_id": variant_m["id"], "quantity": 99},
                {"variant_id": variant_l["id"], "quantity": 99},
                {"variant_id": 999999, "quantity": 1},
            ]
        },
    )
    assert merged.status_code == 200, merged.text
    cart = merged.json()
    quantities = {
        item["variant_id"]: item["quantity"] for item in cart["items"]
    }
    assert quantities[variant_m["id"]] == 8
    assert quantities[variant_l["id"]] == 2
    assert cart["item_count"] == 10
    assert len(cart["items"]) == 2


def test_order_creation_updates_stock_and_clears_cart(
    client, admin_auth, customer_auth, product, order_payload
):
    headers = customer_auth["headers"]
    variant_m = next(
        variant for variant in product["variants"] if variant["size"] == "M"
    )
    variant_l = next(
        variant for variant in product["variants"] if variant["size"] == "L"
    )

    assert _add_to_cart(client, headers, variant_m["id"], 2).status_code == 200
    assert _add_to_cart(client, headers, variant_l["id"], 1).status_code == 200

    created = client.post(
        "/orders", headers=headers, json=order_payload
    )
    assert created.status_code == 201, created.text
    order = created.json()

    expected_subtotal = product["price"] * 3
    assert order["status"] == "pending"
    assert order["payment_method"] == "cod"
    assert order["payment_status"] == "pending"
    assert order["subtotal"] == expected_subtotal
    assert order["shipping_fee"] == 350
    assert order["total"] == expected_subtotal + 350
    assert order["contact_email"] == customer_auth["user"]["email"]
    assert len(order["items"]) == 2
    assert {item["sku"] for item in order["items"]} == {
        variant_m["sku"],
        variant_l["sku"],
    }
    assert sum(item["line_total"] for item in order["items"]) == (
        expected_subtotal
    )

    cart = client.get("/cart", headers=headers)
    assert cart.status_code == 200
    assert cart.json()["items"] == []

    refreshed_product = client.get(
        f"/admin/products/{product['id']}",
        headers=admin_auth["headers"],
    )
    stocks = {
        variant["sku"]: variant["stock"]
        for variant in refreshed_product.json()["variants"]
    }
    assert stocks[variant_m["sku"]] == 6
    assert stocks[variant_l["sku"]] == 1

    history = client.get("/orders", headers=headers)
    assert history.status_code == 200
    assert [item["id"] for item in history.json()] == [order["id"]]

    detail = client.get(f"/orders/{order['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["total"] == order["total"]

    other = client.post(
        "/auth/register",
        json={
            "name": "Other Customer",
            "email": "other@furzy.dev",
            "password": "OtherCustomerPass123!",
        },
    )
    other_headers = {
        "Authorization": f"Bearer {other.json()['access_token']}"
    }
    forbidden_detail = client.get(
        f"/orders/{order['id']}", headers=other_headers
    )
    assert forbidden_detail.status_code == 404
    assert client.get("/orders", headers=other_headers).json() == []


def test_order_requires_a_non_empty_cart(
    client, customer_auth, order_payload
):
    response = client.post(
        "/orders",
        headers=customer_auth["headers"],
        json=order_payload,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Your cart is empty"


def test_cart_rejects_inactive_and_out_of_stock_products(
    client, customer_auth, create_product
):
    inactive = create_product(name="Inactive Tee", is_active=False)
    sold_out = create_product(
        name="Sold Out Tee",
        variants=[
            {
                "size": "M",
                "color": "Black",
                "sku": "SOLD-OUT-M",
                "stock": 0,
            }
        ],
    )
    headers = customer_auth["headers"]

    inactive_response = _add_to_cart(
        client, headers, inactive["variants"][0]["id"], 1
    )
    sold_out_response = _add_to_cart(
        client, headers, sold_out["variants"][0]["id"], 1
    )

    assert inactive_response.status_code == 409
    assert sold_out_response.status_code == 409


def test_order_rejects_stock_lost_after_cart_add(
    client, customer_auth, product, order_payload
):
    headers = customer_auth["headers"]
    variant_m = next(
        variant for variant in product["variants"] if variant["size"] == "M"
    )
    assert _add_to_cart(client, headers, variant_m["id"], 2).status_code == 200

    with SessionLocal() as db:
        variant = db.get(ProductVariant, variant_m["id"])
        variant.stock = 1
        db.commit()

    response = client.post(
        "/orders", headers=headers, json=order_payload
    )
    assert response.status_code == 409
    assert "Only 1" in response.json()["detail"]

    cart = client.get("/cart", headers=headers)
    assert cart.json()["item_count"] == 2

    with SessionLocal() as db:
        variant = db.get(ProductVariant, variant_m["id"])
        assert variant.stock == 1
