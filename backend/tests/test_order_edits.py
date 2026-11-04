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


def _create_order(client, customer_auth, product, order_payload):
    _add_to_cart(
        client, customer_auth["headers"], product, 1
    )
    response = client.post(
        "/orders",
        headers=customer_auth["headers"],
        json=order_payload,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_admin_edits_pending_order_and_records_audit(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
):
    order = _create_order(
        client, customer_auth, product, order_payload
    )

    updated = client.patch(
        f"/admin/orders/{order['id']}",
        headers=admin_auth["headers"],
        json={
            "contact_name": "Updated Customer",
            "contact_email": "Updated.Customer@Example.com",
            "phone": "0779999999",
            "address_line1": "99 Updated Road",
            "address_line2": "Suite 5",
            "city": "Kandy",
            "postal_code": "20000",
            "country": "Sri Lanka",
            "notes": "",
        },
    )
    assert updated.status_code == 200, updated.text
    data = updated.json()
    assert data["contact_name"] == "Updated Customer"
    assert data["contact_email"] == (
        "updated.customer@example.com"
    )
    assert data["phone"] == "0779999999"
    assert data["address_line1"] == "99 Updated Road"
    assert data["address_line2"] == "Suite 5"
    assert data["city"] == "Kandy"
    assert data["postal_code"] == "20000"
    assert data["notes"] == ""

    fetched = client.get(
        f"/admin/orders/{order['id']}",
        headers=admin_auth["headers"],
    ).json()
    assert fetched["contact_name"] == "Updated Customer"
    assert fetched["city"] == "Kandy"

    audit = client.get(
        f"/admin/orders/{order['id']}/audit",
        headers=admin_auth["headers"],
    )
    assert audit.status_code == 200
    events = audit.json()
    assert len(events) == 1
    event = events[0]
    assert event["action"] == "details_edited"
    assert event["actor_user_id"] == admin_auth["user"]["id"]
    assert event["changes"]["contact_name"] == {
        "from": order_payload["contact_name"],
        "to": "Updated Customer",
    }
    assert event["changes"]["contact_email"]["to"] == (
        "updated.customer@example.com"
    )
    assert event["changes"]["notes"] == {
        "from": order_payload["notes"],
        "to": "",
    }

    no_change = client.patch(
        f"/admin/orders/{order['id']}",
        headers=admin_auth["headers"],
        json={"contact_name": "Updated Customer"},
    )
    assert no_change.status_code == 200
    audit = client.get(
        f"/admin/orders/{order['id']}/audit",
        headers=admin_auth["headers"],
    ).json()
    assert len(audit) == 1

    second_change = client.patch(
        f"/admin/orders/{order['id']}",
        headers=admin_auth["headers"],
        json={"city": "Galle"},
    )
    assert second_change.status_code == 200
    audit = client.get(
        f"/admin/orders/{order['id']}/audit",
        headers=admin_auth["headers"],
    ).json()
    assert len(audit) == 2
    assert audit[0]["changes"]["city"] == {
        "from": "Kandy",
        "to": "Galle",
    }

    empty = client.patch(
        f"/admin/orders/{order['id']}",
        headers=admin_auth["headers"],
        json={},
    )
    blank_name = client.patch(
        f"/admin/orders/{order['id']}",
        headers=admin_auth["headers"],
        json={"contact_name": "   "},
    )
    invalid_email = client.patch(
        f"/admin/orders/{order['id']}",
        headers=admin_auth["headers"],
        json={"contact_email": "not-an-email"},
    )
    long_notes = client.patch(
        f"/admin/orders/{order['id']}",
        headers=admin_auth["headers"],
        json={"notes": "x" * 501},
    )
    forbidden_field = client.patch(
        f"/admin/orders/{order['id']}",
        headers=admin_auth["headers"],
        json={"status": "shipped"},
    )
    assert empty.status_code == 422
    assert blank_name.status_code == 422
    assert invalid_email.status_code == 422
    assert long_notes.status_code == 422
    assert forbidden_field.status_code == 422


def test_order_edit_locked_after_shipping_and_access_control(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
):
    order = _create_order(
        client, customer_auth, product, order_payload
    )
    confirmed = client.patch(
        f"/admin/orders/{order['id']}/status",
        headers=admin_auth["headers"],
        json={"status": "confirmed"},
    )
    assert confirmed.status_code == 200

    confirmed_edit = client.patch(
        f"/admin/orders/{order['id']}",
        headers=admin_auth["headers"],
        json={"contact_name": "Confirmed Edit"},
    )
    assert confirmed_edit.status_code == 200

    shipped = client.patch(
        f"/admin/orders/{order['id']}/status",
        headers=admin_auth["headers"],
        json={"status": "shipped"},
    )
    assert shipped.status_code == 200

    blocked = client.patch(
        f"/admin/orders/{order['id']}",
        headers=admin_auth["headers"],
        json={"contact_name": "Too Late"},
    )
    assert blocked.status_code == 409

    customer_edit = client.patch(
        f"/admin/orders/{order['id']}",
        headers=customer_auth["headers"],
        json={"contact_name": "Customer Edit"},
    )
    anonymous_edit = client.patch(
        f"/admin/orders/{order['id']}",
        json={"contact_name": "Anonymous Edit"},
    )
    customer_audit = client.get(
        f"/admin/orders/{order['id']}/audit",
        headers=customer_auth["headers"],
    )
    anonymous_audit = client.get(
        f"/admin/orders/{order['id']}/audit"
    )
    missing_edit = client.patch(
        "/admin/orders/999999",
        headers=admin_auth["headers"],
        json={"contact_name": "Missing"},
    )
    missing_audit = client.get(
        "/admin/orders/999999/audit",
        headers=admin_auth["headers"],
    )

    assert customer_edit.status_code == 403
    assert anonymous_edit.status_code == 401
    assert customer_audit.status_code == 403
    assert anonymous_audit.status_code == 401
    assert missing_edit.status_code == 404
    assert missing_audit.status_code == 404
