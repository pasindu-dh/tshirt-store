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
    payment_method="cod",
    quantity=1,
):
    _add_to_cart(
        client, customer_auth["headers"], product, quantity
    )
    response = client.post(
        "/orders",
        headers=customer_auth["headers"],
        json={**order_payload, "payment_method": payment_method},
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


def _request_return(
    client,
    customer_auth,
    order,
    reason="Item does not fit.",
    items=None,
):
    return client.post(
        f"/orders/{order['id']}/returns",
        headers=customer_auth["headers"],
        json={
            "reason": reason,
            "notes": "Requested by test customer.",
            "items": items
            or [
                {
                    "order_item_id": order["items"][0]["id"],
                    "quantity": 1,
                }
            ],
        },
    )


def test_customer_can_request_return_only_after_delivery(
    client, admin_auth, customer_auth, product, order_payload
):
    order = _create_order(
        client, customer_auth, product, order_payload
    )
    early = _request_return(client, customer_auth, order)
    assert early.status_code == 409

    _deliver_order(client, admin_auth, order)
    created = _request_return(client, customer_auth, order)
    assert created.status_code == 201, created.text
    request = created.json()
    assert request["status"] == "requested"
    assert request["refund"] is None
    assert request["reason"] == "Item does not fit."

    duplicate = _request_return(client, customer_auth, order)
    assert duplicate.status_code == 409

    anonymous = client.get(f"/orders/{order['id']}/returns")
    assert anonymous.status_code == 401

    listing = client.get(
        f"/orders/{order['id']}/returns",
        headers=customer_auth["headers"],
    )
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [
        request["id"]
    ]

    other = client.post(
        "/auth/register",
        json={
            "name": "Return Other",
            "email": "return-other@furzy.dev",
            "password": "ReturnOtherPass123!",
        },
    )
    other_headers = {
        "Authorization": f"Bearer {other.json()['access_token']}"
    }
    assert (
        client.get(
            f"/orders/{order['id']}/returns",
            headers=other_headers,
        ).status_code
        == 404
    )
    assert (
        _request_return(
            client,
            {"headers": other_headers},
            order,
        ).status_code
        == 404
    )


def test_admin_reviews_return_and_customer_sees_status(
    client, admin_auth, customer_auth, product, order_payload
):
    order = _create_order(
        client, customer_auth, product, order_payload
    )
    _deliver_order(client, admin_auth, order)
    request = _request_return(client, customer_auth, order).json()

    admin_list = client.get(
        f"/admin/orders/{order['id']}/returns",
        headers=admin_auth["headers"],
    )
    assert admin_list.status_code == 200
    assert len(admin_list.json()) == 1

    customer_review = client.patch(
        f"/admin/orders/{order['id']}/returns/{request['id']}",
        headers=customer_auth["headers"],
        json={"status": "approved"},
    )
    assert customer_review.status_code == 403

    approved = client.patch(
        f"/admin/orders/{order['id']}/returns/{request['id']}",
        headers=admin_auth["headers"],
        json={
            "status": "approved",
            "note": "Approved after photos were checked.",
        },
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["review_note"].startswith("Approved")

    customer_list = client.get(
        f"/orders/{order['id']}/returns",
        headers=customer_auth["headers"],
    ).json()
    assert customer_list[0]["status"] == "approved"
    assert "Approved" in customer_list[0]["review_note"]

    review_again = client.patch(
        f"/admin/orders/{order['id']}/returns/{request['id']}",
        headers=admin_auth["headers"],
        json={"status": "rejected"},
    )
    assert review_again.status_code == 409


def test_return_rejection_is_visible_to_customer(
    client, admin_auth, customer_auth, product, order_payload
):
    order = _create_order(
        client, customer_auth, product, order_payload
    )
    _deliver_order(client, admin_auth, order)
    request = _request_return(
        client,
        customer_auth,
        order,
        reason="Requesting a different return.",
    ).json()

    rejected = client.patch(
        f"/admin/orders/{order['id']}/returns/{request['id']}",
        headers=admin_auth["headers"],
        json={
            "status": "rejected",
            "note": "Outside the return window.",
        },
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    listed = client.get(
        f"/orders/{order['id']}/returns",
        headers=customer_auth["headers"],
    ).json()
    assert listed[0]["status"] == "rejected"
    assert "return window" in listed[0]["review_note"]


def test_admin_links_refund_to_approved_return(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
):
    order = _create_order(
        client,
        customer_auth,
        product,
        order_payload,
        payment_method="online",
    )
    session = client.post(
        f"/payments/orders/{order['id']}/session",
        headers=customer_auth["headers"],
    )
    assert session.status_code == 200
    complete = client.post(
        f"/payments/orders/{order['id']}/mock-complete",
        headers=customer_auth["headers"],
    )
    assert complete.status_code == 200
    _deliver_order(client, admin_auth, order)

    payments = client.get(
        f"/admin/orders/{order['id']}/payments",
        headers=admin_auth["headers"],
    ).json()
    payment = payments[0]
    refund_response = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/refunds",
        headers=admin_auth["headers"],
        json={
            "kind": "return",
            "amount": 100,
            "reason": "Partial return refund.",
        },
    )
    assert refund_response.status_code == 201, refund_response.text
    refund = refund_response.json()

    request = _request_return(client, customer_auth, order).json()

    early_link = client.patch(
        f"/admin/orders/{order['id']}/returns/{request['id']}/refund",
        headers=admin_auth["headers"],
        json={"refund_id": refund["id"]},
    )
    assert early_link.status_code == 409

    approved = client.patch(
        f"/admin/orders/{order['id']}/returns/{request['id']}",
        headers=admin_auth["headers"],
        json={"status": "approved", "note": "Return accepted."},
    )
    assert approved.status_code == 200

    linked = client.patch(
        f"/admin/orders/{order['id']}/returns/{request['id']}/refund",
        headers=admin_auth["headers"],
        json={"refund_id": refund["id"]},
    )
    assert linked.status_code == 200, linked.text
    assert linked.json()["refund_id"] == refund["id"]
    assert linked.json()["refund"]["status"] == "pending"

    customer_list = client.get(
        f"/orders/{order['id']}/returns",
        headers=customer_auth["headers"],
    ).json()
    assert customer_list[0]["refund_id"] == refund["id"]
    assert customer_list[0]["refund"]["amount"] == 100
    assert customer_list[0]["refund"]["status"] == "pending"

    missing_refund = client.patch(
        f"/admin/orders/{order['id']}/returns/{request['id']}/refund",
        headers=admin_auth["headers"],
        json={"refund_id": 999999},
    )
    assert missing_refund.status_code == 404


def test_return_link_rejects_invalid_refund_and_customer_access(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
):
    order = _create_order(
        client, customer_auth, product, order_payload
    )
    _deliver_order(client, admin_auth, order)
    request = _request_return(client, customer_auth, order).json()

    customer_link = client.patch(
        f"/admin/orders/{order['id']}/returns/{request['id']}",
        headers=customer_auth["headers"],
        json={"status": "approved"},
    )
    assert customer_link.status_code == 403

    anonymous_list = client.get(
        f"/admin/orders/{order['id']}/returns"
    )
    assert anonymous_list.status_code == 401

    duplicate = _request_return(
        client,
        customer_auth,
        order,
        reason="Duplicate request.",
    )
    assert duplicate.status_code == 409


def test_return_items_are_restocked_only_on_completion(
    client, admin_auth, customer_auth, product, order_payload
):
    from app.database import SessionLocal
    from app.models import ProductVariant

    order = _create_order(
        client,
        customer_auth,
        product,
        order_payload,
        quantity=2,
    )
    _deliver_order(client, admin_auth, order)
    variant_id = product["variants"][0]["id"]

    with SessionLocal() as db:
        assert db.get(ProductVariant, variant_id).stock == 6

    request = _request_return(
        client,
        customer_auth,
        order,
        items=[
            {
                "order_item_id": order["items"][0]["id"],
                "quantity": 1,
            }
        ],
    )
    assert request.status_code == 201
    request_id = request.json()["id"]
    assert len(request.json()["items"]) == 1
    assert request.json()["items"][0]["quantity"] == 1

    approved = client.patch(
        f"/admin/orders/{order['id']}/returns/{request_id}",
        headers=admin_auth["headers"],
        json={"status": "approved", "note": "Approved."},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    with SessionLocal() as db:
        assert db.get(ProductVariant, variant_id).stock == 6

    completed = client.patch(
        f"/admin/orders/{order['id']}/returns/{request_id}",
        headers=admin_auth["headers"],
        json={
            "status": "completed",
            "note": "Item received and inspected.",
        },
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"
    assert completed.json()["stock_restocked_at"] is not None
    assert completed.json()["items"][0]["restocked_at"] is not None

    with SessionLocal() as db:
        assert db.get(ProductVariant, variant_id).stock == 7

    duplicate = client.patch(
        f"/admin/orders/{order['id']}/returns/{request_id}",
        headers=admin_auth["headers"],
        json={"status": "completed", "note": "Again."},
    )
    assert duplicate.status_code == 409

    with SessionLocal() as db:
        assert db.get(ProductVariant, variant_id).stock == 7


def test_customer_can_cancel_pending_return_and_reapply(
    client, admin_auth, customer_auth, product, order_payload
):
    order = _create_order(
        client, customer_auth, product, order_payload
    )
    _deliver_order(client, admin_auth, order)
    request = _request_return(client, customer_auth, order).json()

    cancelled = client.post(
        f"/orders/{order['id']}/returns/{request['id']}/cancel",
        headers=customer_auth["headers"],
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    review_cancelled = client.patch(
        f"/admin/orders/{order['id']}/returns/{request['id']}",
        headers=admin_auth["headers"],
        json={"status": "approved"},
    )
    assert review_cancelled.status_code == 409

    reapplied = _request_return(
        client,
        customer_auth,
        order,
        reason="Second return request after cancellation.",
    )
    assert reapplied.status_code == 201
    assert reapplied.json()["status"] == "requested"


def test_return_item_quantity_and_ownership_validation(
    client, admin_auth, customer_auth, product, order_payload
):
    order = _create_order(
        client, customer_auth, product, order_payload
    )
    _deliver_order(client, admin_auth, order)
    order_item_id = order["items"][0]["id"]

    too_many = _request_return(
        client,
        customer_auth,
        order,
        items=[{"order_item_id": order_item_id, "quantity": 2}],
    )
    assert too_many.status_code == 400
    assert "Only 1" in too_many.json()["detail"]

    invalid_item = _request_return(
        client,
        customer_auth,
        order,
        items=[{"order_item_id": 999999, "quantity": 1}],
    )
    assert invalid_item.status_code == 400

    duplicate_items = _request_return(
        client,
        customer_auth,
        order,
        items=[
            {"order_item_id": order_item_id, "quantity": 1},
            {"order_item_id": order_item_id, "quantity": 1},
        ],
    )
    assert duplicate_items.status_code == 422

    # A valid request still works after the rejected attempts.
    valid = _request_return(client, customer_auth, order)
    assert valid.status_code == 201


def test_admin_global_return_queue(
    client, admin_auth, customer_auth, product, order_payload
):
    order = _create_order(
        client, customer_auth, product, order_payload
    )
    _deliver_order(client, admin_auth, order)
    request = _request_return(client, customer_auth, order).json()

    customer = client.get(
        "/admin/returns", headers=customer_auth["headers"]
    )
    anonymous = client.get("/admin/returns")
    assert customer.status_code == 403
    assert anonymous.status_code == 401

    listing = client.get(
        "/admin/returns", headers=admin_auth["headers"]
    )
    assert listing.status_code == 200
    assert listing.headers["X-Total-Count"] == "1"
    item = listing.json()[0]
    assert item["id"] == request["id"]
    assert item["order_id"] == order["id"]
    assert item["item_count"] == 1
    assert item["order_contact_name"] == order["contact_name"]

    filtered = client.get(
        "/admin/returns",
        headers=admin_auth["headers"],
        params={"status": "requested"},
    )
    assert filtered.headers["X-Total-Count"] == "1"

    no_matches = client.get(
        "/admin/returns",
        headers=admin_auth["headers"],
        params={"search": "not-a-customer"},
    )
    assert no_matches.headers["X-Total-Count"] == "0"

    by_email = client.get(
        "/admin/returns",
        headers=admin_auth["headers"],
        params={"search": customer_auth["user"]["email"]},
    )
    assert by_email.headers["X-Total-Count"] == "1"


def test_return_status_emails_are_scheduled(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
    monkeypatch,
):
    customer_calls = []
    admin_calls = []
    monkeypatch.setattr(
        "app.routers.returns.send_return_status_update",
        lambda *args: customer_calls.append(args),
    )
    monkeypatch.setattr(
        "app.routers.admin_orders.send_return_status_update",
        lambda *args: admin_calls.append(args),
    )

    order = _create_order(
        client, customer_auth, product, order_payload
    )
    _deliver_order(client, admin_auth, order)
    request = _request_return(client, customer_auth, order).json()
    request_id = request["id"]

    assert len(customer_calls) == 1
    assert customer_calls[0][0] == order["contact_email"]
    assert customer_calls[0][3] == "requested"

    approved = client.patch(
        f"/admin/orders/{order['id']}/returns/{request_id}",
        headers=admin_auth["headers"],
        json={"status": "approved", "note": "Approved by email test."},
    )
    assert approved.status_code == 200
    assert len(admin_calls) == 1
    assert admin_calls[0][3] == "approved"

    completed = client.patch(
        f"/admin/orders/{order['id']}/returns/{request_id}",
        headers=admin_auth["headers"],
        json={"status": "completed", "note": "Received."},
    )
    assert completed.status_code == 200
    assert len(admin_calls) == 2
    assert admin_calls[1][3] == "completed"
