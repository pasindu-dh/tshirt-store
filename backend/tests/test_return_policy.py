from datetime import timedelta

from app.config import settings
from app.database import SessionLocal
from app.models import Order
from app.models.common import utcnow


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


def _deliver_order(client, admin_auth, order):
    for status in ("confirmed", "shipped", "delivered"):
        response = client.patch(
            f"/admin/orders/{order['id']}/status",
            headers=admin_auth["headers"],
            json={"status": status},
        )
        assert response.status_code == 200, response.text
    return response.json()


def _request_return(client, customer_auth, order, **overrides):
    payload = {
        "reason_code": "size_fit",
        "reason": "The fit is not right.",
        "items": [
            {
                "order_item_id": order["items"][0]["id"],
                "quantity": 1,
            }
        ],
        **overrides,
    }
    return client.post(
        f"/orders/{order['id']}/returns",
        headers=customer_auth["headers"],
        json=payload,
    )


def _set_delivered_at(order_id, value):
    with SessionLocal() as db:
        order = db.get(Order, order_id)
        order.delivered_at = value
        db.commit()


def test_return_policy_and_delivery_timestamp(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
):
    policy = client.get("/returns/policy")
    assert policy.status_code == 200
    data = policy.json()
    assert data["window_days"] == settings.return_window_days
    assert data["policy_text"]
    reasons = {
        item["code"]: item["label"]
        for item in data["reasons"]
    }
    assert reasons["size_fit"] == "Size or fit"
    assert reasons["damaged"] == "Item arrived damaged"
    assert reasons["other"] == "Other"

    order = _create_order(
        client, customer_auth, product, order_payload
    )
    delivered = _deliver_order(client, admin_auth, order)
    assert delivered["delivered_at"] is not None

    fetched = client.get(
        f"/orders/{order['id']}",
        headers=customer_auth["headers"],
    )
    assert fetched.status_code == 200
    assert fetched.json()["delivered_at"] is not None

    request = _request_return(
        client,
        customer_auth,
        order,
        reason_code="damaged",
        reason="The shirt arrived with a tear.",
    )
    assert request.status_code == 201, request.text
    assert request.json()["reason_code"] == "damaged"

    listed = client.get(
        f"/orders/{order['id']}/returns",
        headers=customer_auth["headers"],
    ).json()
    assert listed[0]["reason_code"] == "damaged"

    invalid = _request_return(
        client,
        customer_auth,
        order,
        reason_code="not-a-reason",
    )
    assert invalid.status_code == 422


def test_return_window_rejects_late_requests(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
    monkeypatch,
):
    order = _create_order(
        client, customer_auth, product, order_payload
    )
    _deliver_order(client, admin_auth, order)
    _set_delivered_at(
        order["id"],
        utcnow() - timedelta(
            days=settings.return_window_days + 1
        ),
    )

    late = _request_return(client, customer_auth, order)
    assert late.status_code == 409
    assert "days of delivery" in late.json()["detail"]

    monkeypatch.setattr(
        settings, "return_window_days", 0
    )
    allowed = _request_return(client, customer_auth, order)
    assert allowed.status_code == 201, allowed.text
    assert allowed.json()["reason_code"] == "size_fit"
