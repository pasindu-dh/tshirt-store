from datetime import timedelta

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import Coupon, Order, Payment, ProductVariant
from app.models.common import utcnow
from app.services.stock import expire_unpaid_online_orders


def _add_to_cart(client, headers, product, quantity=1):
    variant = product["variants"][0]
    response = client.post(
        "/cart/items",
        headers=headers,
        json={"variant_id": variant["id"], "quantity": quantity},
    )
    assert response.status_code == 200, response.text
    return variant


def _create_online_order(
    client,
    customer_auth,
    product,
    order_payload,
    quantity=1,
    coupon_code=None,
):
    variant = _add_to_cart(
        client, customer_auth["headers"], product, quantity
    )
    payload = {
        **order_payload,
        "payment_method": "online",
    }

    if coupon_code:
        payload["coupon_code"] = coupon_code

    response = client.post(
        "/orders",
        headers=customer_auth["headers"],
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json(), variant


def _expire_order(order_id):
    with SessionLocal() as db:
        order = db.get(Order, order_id)
        order.reservation_expires_at = utcnow() - timedelta(
            minutes=1
        )
        db.commit()


def _stock(variant_id):
    with SessionLocal() as db:
        return db.get(ProductVariant, variant_id).stock


def test_expired_online_order_releases_stock_and_payment_once(
    client, customer_auth, product, order_payload
):
    order, variant = _create_online_order(
        client, customer_auth, product, order_payload
    )
    session = client.post(
        f"/payments/orders/{order['id']}/session",
        headers=customer_auth["headers"],
    )
    assert session.status_code == 200
    assert _stock(variant["id"]) == 7
    _expire_order(order["id"])

    with SessionLocal() as db:
        assert expire_unpaid_online_orders(db) == 1

    expired = client.get(
        f"/orders/{order['id']}",
        headers=customer_auth["headers"],
    ).json()
    assert expired["status"] == "cancelled"
    assert expired["payment_status"] == "cancelled"
    assert expired["stock_released_at"] is not None
    assert expired["stock_release_reason"] == "expired"
    assert expired["reservation_expires_at"] is not None
    assert _stock(variant["id"]) == 8

    with SessionLocal() as db:
        payment = db.scalar(
            select(Payment).where(Payment.order_id == order["id"])
        )
        assert payment.status == "cancelled"
        assert len(payment.events) == 2
        assert payment.events[-1].source == "system"

        assert expire_unpaid_online_orders(db) == 0

    assert _stock(variant["id"]) == 8


def test_expiry_restores_coupon_usage_once(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
):
    coupon_response = client.post(
        "/admin/coupons",
        headers=admin_auth["headers"],
        json={
            "code": "EXPIRY10",
            "description": "Expiry test",
            "discount_type": "percent",
            "value": 10,
            "min_subtotal": 0,
            "usage_limit": 1,
            "is_active": True,
        },
    )
    assert coupon_response.status_code == 201

    order, variant = _create_online_order(
        client,
        customer_auth,
        product,
        order_payload,
        coupon_code="EXPIRY10",
    )
    with SessionLocal() as db:
        coupon = db.scalar(
            select(Coupon).where(Coupon.code == "EXPIRY10")
        )
        assert coupon.used_count == 1

    _expire_order(order["id"])

    with SessionLocal() as db:
        assert expire_unpaid_online_orders(db) == 1
        coupon = db.scalar(
            select(Coupon).where(Coupon.code == "EXPIRY10")
        )
        assert coupon.used_count == 0
        assert expire_unpaid_online_orders(db) == 0
        coupon = db.scalar(
            select(Coupon).where(Coupon.code == "EXPIRY10")
        )
        assert coupon.used_count == 0

    assert _stock(variant["id"]) == 8


def test_paid_online_order_is_not_expired(
    client, customer_auth, product, order_payload
):
    order, variant = _create_online_order(
        client, customer_auth, product, order_payload
    )
    client.post(
        f"/payments/orders/{order['id']}/session",
        headers=customer_auth["headers"],
    )
    paid = client.post(
        f"/payments/orders/{order['id']}/mock-complete",
        headers=customer_auth["headers"],
    )
    assert paid.status_code == 200
    _expire_order(order["id"])

    with SessionLocal() as db:
        assert expire_unpaid_online_orders(db) == 0

    current = client.get(
        f"/orders/{order['id']}",
        headers=customer_auth["headers"],
    ).json()
    assert current["status"] == "pending"
    assert current["payment_status"] == "paid"
    assert current["stock_released_at"] is None
    assert _stock(variant["id"]) == 7


def test_cancelled_order_is_not_released_twice_by_expiry(
    client, admin_auth, customer_auth, product, order_payload
):
    order, variant = _create_online_order(
        client, customer_auth, product, order_payload
    )
    session = client.post(
        f"/payments/orders/{order['id']}/session",
        headers=customer_auth["headers"],
    )
    assert session.status_code == 200
    cancelled = client.patch(
        f"/admin/orders/{order['id']}/status",
        headers=admin_auth["headers"],
        json={"status": "cancelled"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["stock_release_reason"] == "cancelled"

    with SessionLocal() as db:
        payment = db.scalar(
            select(Payment).where(Payment.order_id == order["id"])
        )
        assert payment.status == "cancelled"
        assert payment.events[-1].status == "cancelled"

    _expire_order(order["id"])

    with SessionLocal() as db:
        assert expire_unpaid_online_orders(db) == 0

    current = client.get(
        f"/admin/orders/{order['id']}",
        headers=admin_auth["headers"],
    ).json()
    assert current["stock_release_reason"] == "cancelled"
    assert _stock(variant["id"]) == 8


def test_released_stock_can_be_sold_without_double_release(
    client, customer_auth, product, order_payload
):
    first_order, variant = _create_online_order(
        client,
        customer_auth,
        product,
        order_payload,
        quantity=8,
    )
    assert _stock(variant["id"]) == 0
    _expire_order(first_order["id"])

    with SessionLocal() as db:
        assert expire_unpaid_online_orders(db) == 1

    second = client.post(
        "/auth/register",
        json={
            "name": "Second Buyer",
            "email": "second-buyer@furzy.dev",
            "password": "SecondBuyerPass123!",
        },
    )
    second_headers = {
        "Authorization": f"Bearer {second.json()['access_token']}"
    }
    _add_to_cart(client, second_headers, product, 8)
    second_order = client.post(
        "/orders",
        headers=second_headers,
        json=order_payload,
    )
    assert second_order.status_code == 201
    assert _stock(variant["id"]) == 0

    with SessionLocal() as db:
        pending_count = db.scalar(
            select(func.count(Payment.id)).where(
                Payment.order_id == first_order["id"],
                Payment.status == "pending",
            )
        )
        assert pending_count == 0

    assert _stock(variant["id"]) == 0
