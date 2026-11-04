from datetime import datetime, timezone


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


def _create_paid_order(
    client, customer_auth, product, order_payload
):
    _add_to_cart(
        client, customer_auth["headers"], product, 1
    )
    order = client.post(
        "/orders",
        headers=customer_auth["headers"],
        json={**order_payload, "payment_method": "online"},
    )
    assert order.status_code == 201, order.text
    order_data = order.json()

    session = client.post(
        f"/payments/orders/{order_data['id']}/session",
        headers=customer_auth["headers"],
    )
    complete = client.post(
        f"/payments/orders/{order_data['id']}/mock-complete",
        headers=customer_auth["headers"],
    )
    assert session.status_code == 200
    assert complete.status_code == 200
    return order_data


def _deliver_order(client, admin_auth, order):
    for status in ("confirmed", "shipped", "delivered"):
        response = client.patch(
            f"/admin/orders/{order['id']}/status",
            headers=admin_auth["headers"],
            json={"status": status},
        )
        assert response.status_code == 200, response.text


def _payment(client, admin_auth, order):
    payments = client.get(
        f"/admin/orders/{order['id']}/payments",
        headers=admin_auth["headers"],
    )
    assert payments.status_code == 200
    return payments.json()[0]


def _create_refund(
    client,
    admin_auth,
    order,
    payment,
    *,
    kind,
    amount,
    reason,
):
    response = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/refunds",
        headers=admin_auth["headers"],
        json={
            "kind": kind,
            "amount": amount,
            "reason": reason,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _list_refunds(client, admin_auth, **params):
    response = client.get(
        "/admin/refunds",
        headers=admin_auth["headers"],
        params=params,
    )
    assert response.status_code == 200, response.text
    return response.json(), int(
        response.headers["X-Total-Count"]
    )


def test_global_refund_queue_filters_and_fields(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
):
    order = _create_paid_order(
        client, customer_auth, product, order_payload
    )
    _deliver_order(client, admin_auth, order)
    payment = _payment(client, admin_auth, order)

    completed = _create_refund(
        client,
        admin_auth,
        order,
        payment,
        kind="refund",
        amount=1000,
        reason="Alpha queue refund.",
    )
    marked = client.patch(
        f"/admin/orders/{order['id']}/refunds/{completed['id']}",
        headers=admin_auth["headers"],
        json={"status": "refunded", "note": "Completed."},
    )
    assert marked.status_code == 200

    pending = _create_refund(
        client,
        admin_auth,
        order,
        payment,
        kind="return",
        amount=500,
        reason="Beta queue return.",
    )

    refunds, total = _list_refunds(client, admin_auth)
    assert total == 2
    assert [item["id"] for item in refunds] == [
        pending["id"],
        completed["id"],
    ]

    queue_item = refunds[0]
    assert queue_item["order_id"] == order["id"]
    assert queue_item["payment_id"] == payment["id"]
    assert queue_item["payment_reference"] == payment["reference"]
    assert queue_item["order_contact_name"] == (
        order_payload["contact_name"]
    )
    assert queue_item["order_contact_email"] == (
        customer_auth["user"]["email"]
    )
    assert queue_item["order_total"] == order["total"]
    assert queue_item["order_status"] == "delivered"
    assert queue_item["order_payment_status"] == "paid"
    assert queue_item["kind"] == "return"
    assert queue_item["status"] == "pending"
    assert queue_item["amount"] == 500
    assert queue_item["completed_at"] is None

    only_refunded, count = _list_refunds(
        client, admin_auth, status="refunded"
    )
    assert count == 1
    assert only_refunded[0]["id"] == completed["id"]
    assert only_refunded[0]["completed_at"] is not None

    only_returns, count = _list_refunds(
        client, admin_auth, kind="return"
    )
    assert count == 1
    assert only_returns[0]["id"] == pending["id"]

    by_email, count = _list_refunds(
        client,
        admin_auth,
        search=customer_auth["user"]["email"],
    )
    assert count == 2

    by_order, count = _list_refunds(
        client, admin_auth, search=str(order["id"])
    )
    assert count == 2

    by_refund, count = _list_refunds(
        client, admin_auth, search=str(pending["id"])
    )
    assert count == 1
    assert by_refund[0]["id"] == pending["id"]

    by_reason, count = _list_refunds(
        client, admin_auth, search="Beta"
    )
    assert count == 1
    assert by_reason[0]["id"] == pending["id"]

    by_reference, count = _list_refunds(
        client,
        admin_auth,
        search=payment["reference"],
    )
    assert count == 2

    today = datetime.now(timezone.utc).date().isoformat()
    dated, count = _list_refunds(
        client,
        admin_auth,
        date_from=today,
        date_to=today,
    )
    assert count == 2
    assert dated

    page, count = _list_refunds(
        client, admin_auth, page=1, limit=1
    )
    assert count == 2
    assert len(page) == 1


def test_global_refund_queue_access_and_date_validation(
    client,
    admin_auth,
    customer_auth,
):
    customer_access = client.get(
        "/admin/refunds",
        headers=customer_auth["headers"],
    )
    anonymous_access = client.get("/admin/refunds")
    invalid_range = client.get(
        "/admin/refunds",
        headers=admin_auth["headers"],
        params={
            "date_from": "2026-06-01",
            "date_to": "2026-05-01",
        },
    )
    invalid_status = client.get(
        "/admin/refunds",
        headers=admin_auth["headers"],
        params={"status": "not-a-status"},
    )

    assert customer_access.status_code == 403
    assert anonymous_access.status_code == 401
    assert invalid_range.status_code == 400
    assert invalid_status.status_code == 422
