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
    *,
    payment_method="cod",
    quantity=1,
):
    _add_to_cart(
        client,
        customer_auth["headers"],
        product,
        quantity,
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


def _request_return(client, customer_auth, order):
    response = client.post(
        f"/orders/{order['id']}/returns",
        headers=customer_auth["headers"],
        json={
            "reason": "Customer management test.",
            "items": [
                {
                    "order_item_id": order["items"][0]["id"],
                    "quantity": 1,
                }
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _customer_by_email(customers, email):
    return next(
        customer
        for customer in customers
        if customer["email"] == email
    )


def test_admin_customer_directory_and_detail(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
):
    delivered = _create_order(
        client, customer_auth, product, order_payload
    )
    _deliver_order(client, admin_auth, delivered)
    cancelled = _create_order(
        client, customer_auth, product, order_payload
    )
    cancelled_response = client.patch(
        f"/admin/orders/{cancelled['id']}/status",
        headers=admin_auth["headers"],
        json={"status": "cancelled"},
    )
    assert cancelled_response.status_code == 200
    return_request = _request_return(
        client, customer_auth, delivered
    )

    other = client.post(
        "/auth/register",
        json={
            "name": "Other Customer",
            "email": "customer-directory-other@furzy.dev",
            "password": "OtherCustomerPass123!",
        },
    )
    assert other.status_code == 201
    other_user = other.json()["user"]

    listing = client.get(
        "/admin/customers",
        headers=admin_auth["headers"],
    )
    assert listing.status_code == 200
    assert listing.headers["X-Total-Count"] == "2"
    customers = listing.json()
    assert {
        customer["id"] for customer in customers
    } == {customer_auth["user"]["id"], other_user["id"]}
    assert admin_auth["user"]["id"] not in {
        customer["id"] for customer in customers
    }

    active = _customer_by_email(
        customers, customer_auth["user"]["email"]
    )
    assert active["order_count"] == 2
    assert active["delivered_orders"] == 1
    assert active["cancelled_orders"] == 1
    assert active["gross_spend"] == delivered["total"]
    assert active["refunded_total"] == 0
    assert active["pending_refund_total"] == 0
    assert active["net_spend"] == delivered["total"]
    assert active["returns_count"] == 1
    assert active["open_returns"] == 1
    assert active["last_order_at"] is not None

    inactive = _customer_by_email(
        customers, other_user["email"]
    )
    assert inactive["order_count"] == 0
    assert inactive["gross_spend"] == 0
    assert inactive["net_spend"] == 0
    assert inactive["returns_count"] == 0
    assert inactive["last_order_at"] is None

    search = client.get(
        "/admin/customers",
        headers=admin_auth["headers"],
        params={"search": customer_auth["user"]["email"]},
    )
    assert search.headers["X-Total-Count"] == "1"
    assert search.json()[0]["id"] == customer_auth["user"]["id"]

    numeric_search = client.get(
        "/admin/customers",
        headers=admin_auth["headers"],
        params={"search": str(customer_auth["user"]["id"])},
    )
    assert numeric_search.headers["X-Total-Count"] == "1"

    no_matches = client.get(
        "/admin/customers",
        headers=admin_auth["headers"],
        params={"search": "does-not-exist"},
    )
    assert no_matches.headers["X-Total-Count"] == "0"

    detail = client.get(
        f"/admin/customers/{customer_auth['user']['id']}",
        headers=admin_auth["headers"],
    )
    assert detail.status_code == 200, detail.text
    detail_data = detail.json()
    assert detail_data["name"] == customer_auth["user"]["name"]
    assert detail_data["order_count"] == 2
    assert detail_data["net_spend"] == delivered["total"]
    assert len(detail_data["orders"]) == 2
    assert len(detail_data["returns"]) == 1
    assert detail_data["returns"][0]["id"] == return_request["id"]
    assert detail_data["orders"][0]["id"] == cancelled["id"]

    missing = client.get(
        "/admin/customers/999999",
        headers=admin_auth["headers"],
    )
    admin_as_customer = client.get(
        f"/admin/customers/{admin_auth['user']['id']}",
        headers=admin_auth["headers"],
    )
    customer_access = client.get(
        "/admin/customers",
        headers=customer_auth["headers"],
    )
    anonymous = client.get("/admin/customers")
    assert missing.status_code == 404
    assert admin_as_customer.status_code == 404
    assert customer_access.status_code == 403
    assert anonymous.status_code == 401


def test_customer_spend_nets_completed_refunds(
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
    complete = client.post(
        f"/payments/orders/{order['id']}/mock-complete",
        headers=customer_auth["headers"],
    )
    assert session.status_code == 200
    assert complete.status_code == 200
    _deliver_order(client, admin_auth, order)

    payments = client.get(
        f"/admin/orders/{order['id']}/payments",
        headers=admin_auth["headers"],
    ).json()
    payment = payments[0]

    completed_refund = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/refunds",
        headers=admin_auth["headers"],
        json={
            "kind": "refund",
            "amount": 1000,
            "reason": "Completed customer refund.",
        },
    )
    assert completed_refund.status_code == 201
    refund_id = completed_refund.json()["id"]
    marked = client.patch(
        f"/admin/orders/{order['id']}/refunds/{refund_id}",
        headers=admin_auth["headers"],
        json={
            "status": "refunded",
            "note": "Refund completed.",
        },
    )
    assert marked.status_code == 200

    pending_refund = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/refunds",
        headers=admin_auth["headers"],
        json={
            "kind": "refund",
            "amount": 500,
            "reason": "Pending customer refund.",
        },
    )
    assert pending_refund.status_code == 201

    detail = client.get(
        f"/admin/customers/{customer_auth['user']['id']}",
        headers=admin_auth["headers"],
    )
    assert detail.status_code == 200
    data = detail.json()
    assert data["gross_spend"] == order["total"]
    assert data["refunded_total"] == 1000
    assert data["pending_refund_total"] == 500
    assert data["net_spend"] == order["total"] - 1000
    assert data["delivered_orders"] == 1
