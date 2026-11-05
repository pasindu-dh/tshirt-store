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


def _place_order(client, customer_auth, product, order_payload):
    _add_to_cart(
        client, customer_auth["headers"], product
    )
    response = client.post(
        "/orders",
        headers=customer_auth["headers"],
        json=order_payload,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _set_status(client, admin_auth, order_id, status):
    response = client.patch(
        f"/admin/orders/{order_id}/status",
        headers=admin_auth["headers"],
        json={"status": status},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _activity(client, admin_auth, order_id):
    response = client.get(
        f"/admin/orders/{order_id}/activity",
        headers=admin_auth["headers"],
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_order_activity_consolidates_order_events(
    client, admin_auth, customer_auth, product, order_payload
):
    order = _place_order(
        client, customer_auth, product, order_payload
    )
    _set_status(client, admin_auth, order["id"], "confirmed")
    edited = client.patch(
        f"/admin/orders/{order['id']}",
        headers=admin_auth["headers"],
        json={"phone": "0779999999", "notes": "Updated in test"},
    )
    assert edited.status_code == 200, edited.text
    _set_status(client, admin_auth, order["id"], "shipped")
    _set_status(client, admin_auth, order["id"], "delivered")

    return_response = client.post(
        f"/orders/{order['id']}/returns",
        headers=customer_auth["headers"],
        json={
            "reason": "Activity test return",
            "items": [
                {
                    "order_item_id": order["items"][0]["id"],
                    "quantity": 1,
                }
            ],
        },
    )
    assert return_response.status_code == 201, return_response.text
    return_id = return_response.json()["id"]

    approved = client.patch(
        f"/admin/orders/{order['id']}/returns/{return_id}",
        headers=admin_auth["headers"],
        json={"status": "approved", "note": "Approved in test."},
    )
    assert approved.status_code == 200, approved.text
    completed = client.patch(
        f"/admin/orders/{order['id']}/returns/{return_id}",
        headers=admin_auth["headers"],
        json={"status": "completed"},
    )
    assert completed.status_code == 200, completed.text

    events = _activity(client, admin_auth, order["id"])
    titles = [event["title"] for event in events]
    assert titles[0] == "Order placed"
    assert "Order confirmed" in titles
    assert "Order details updated" in titles
    assert "Order shipped" in titles
    assert "Order delivered" in titles
    assert f"Return #{return_id} requested" in titles
    assert f"Return #{return_id} completed" in titles

    created = events[0]
    assert created["type"] == "order"
    assert created["actor"] == "Test Customer"
    assert "LKR" in created["description"]

    details = next(
        event
        for event in events
        if event["title"] == "Order details updated"
    )
    assert details["actor"] == "Test Admin"
    assert "phone: 0771234567" in details["description"]
    assert "0779999999" in details["description"]

    timestamps = [event["created_at"] for event in events]
    assert timestamps == sorted(timestamps)


def test_order_activity_requires_admin(
    client, customer_auth, product, order_payload
):
    order = _place_order(
        client, customer_auth, product, order_payload
    )

    anonymous = client.get(
        f"/admin/orders/{order['id']}/activity"
    )
    assert anonymous.status_code == 401

    customer = client.get(
        f"/admin/orders/{order['id']}/activity",
        headers=customer_auth["headers"],
    )
    assert customer.status_code == 403


def test_order_activity_unknown_order(client, admin_auth):
    response = client.get(
        "/admin/orders/999999/activity",
        headers=admin_auth["headers"],
    )
    assert response.status_code == 404
