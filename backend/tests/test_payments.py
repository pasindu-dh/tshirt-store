import hashlib

import pytest

from app.config import Settings, settings, validate_payment_security


def _secret_hash(secret: str) -> str:
    return hashlib.md5(secret.encode("utf-8")).hexdigest().upper()


def _signature(*parts: str) -> str:
    return hashlib.md5(
        "".join(parts).encode("utf-8")
    ).hexdigest().upper()


def _add_to_cart(client, headers, product, quantity=1):
    variant = product["variants"][0]
    response = client.post(
        "/cart/items",
        headers=headers,
        json={"variant_id": variant["id"], "quantity": quantity},
    )
    assert response.status_code == 200, response.text


def _create_online_order(
    client, customer_auth, product, order_payload
):
    _add_to_cart(client, customer_auth["headers"], product, 1)
    response = client.post(
        "/orders",
        headers=customer_auth["headers"],
        json={**order_payload, "payment_method": "online"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _configure_payhere(monkeypatch):
    monkeypatch.setattr(settings, "payment_provider", "payhere")
    monkeypatch.setattr(settings, "payment_mock_enabled", False)
    monkeypatch.setattr(settings, "payhere_merchant_id", "test-merchant")
    monkeypatch.setattr(
        settings, "payhere_merchant_secret", "test-secret"
    )
    monkeypatch.setattr(settings, "payhere_sandbox", True)


def _payhere_notify(
    client,
    reference,
    amount,
    status_code,
    *,
    payment_id="payhere-payment-1",
):
    secret_hash = _secret_hash("test-secret")
    return client.post(
        "/payments/payhere/notify",
        data={
            "merchant_id": "test-merchant",
            "order_id": reference,
            "payment_id": payment_id,
            "payhere_amount": amount,
            "payhere_currency": "LKR",
            "status_code": status_code,
            "md5sig": _signature(
                "test-merchant",
                reference,
                amount,
                "LKR",
                status_code,
                secret_hash,
            ),
        },
    )


def test_payment_config_exposes_no_secrets(client):
    response = client.get("/payments/config")

    assert response.status_code == 200
    data = response.json()
    assert data == {
        "provider": "mock",
        "online_enabled": True,
        "currency": "LKR",
        "mock_enabled": True,
    }


def test_mock_online_order_can_be_paid(
    client, customer_auth, product, order_payload
):
    order = _create_online_order(
        client, customer_auth, product, order_payload
    )
    assert order["payment_method"] == "online"
    assert order["payment_status"] == "pending"

    session = client.post(
        f"/payments/orders/{order['id']}/session",
        headers=customer_auth["headers"],
    )
    assert session.status_code == 200, session.text
    session_data = session.json()
    assert session_data["provider"] == "mock"
    assert session_data["mock"] is True
    assert session_data["action_url"] is None
    assert session_data["order_id"] == order["id"]

    completed = client.post(
        f"/payments/orders/{order['id']}/mock-complete",
        headers=customer_auth["headers"],
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "paid"

    paid_order = client.get(
        f"/orders/{order['id']}",
        headers=customer_auth["headers"],
    )
    assert paid_order.json()["payment_status"] == "paid"

    completed_again = client.post(
        f"/payments/orders/{order['id']}/mock-complete",
        headers=customer_auth["headers"],
    )
    assert completed_again.status_code == 200
    assert completed_again.json()["status"] == "paid"


def test_online_payment_can_be_disabled(
    client, customer_auth, product, order_payload, monkeypatch
):
    monkeypatch.setattr(settings, "payment_provider", "disabled")

    config = client.get("/payments/config").json()
    assert config["online_enabled"] is False

    _add_to_cart(client, customer_auth["headers"], product, 1)
    response = client.post(
        "/orders",
        headers=customer_auth["headers"],
        json={**order_payload, "payment_method": "online"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Online payment is not available."


def test_payment_session_requires_ownership_and_online_method(
    client, customer_auth, product, order_payload
):
    other = client.post(
        "/auth/register",
        json={
            "name": "Other Payer",
            "email": "other-payer@furzy.dev",
            "password": "OtherPayerPass123!",
        },
    )
    other_headers = {
        "Authorization": f"Bearer {other.json()['access_token']}"
    }

    _add_to_cart(client, customer_auth["headers"], product, 1)
    cod_order = client.post(
        "/orders",
        headers=customer_auth["headers"],
        json=order_payload,
    )
    assert cod_order.status_code == 201

    cod_session = client.post(
        f"/payments/orders/{cod_order.json()['id']}/session",
        headers=customer_auth["headers"],
    )
    assert cod_session.status_code == 400

    online_order = _create_online_order(
        client, customer_auth, product, order_payload
    )

    missing = client.post(
        f"/payments/orders/{online_order['id']}/session",
        headers=other_headers,
    )
    assert missing.status_code == 404

    mock_other = client.post(
        f"/payments/orders/{online_order['id']}/mock-complete",
        headers=other_headers,
    )
    assert mock_other.status_code == 404


def test_payhere_session_signature_and_notification(
    client, customer_auth, product, order_payload, monkeypatch
):
    monkeypatch.setattr(settings, "payment_provider", "payhere")
    monkeypatch.setattr(settings, "payhere_merchant_id", "test-merchant")
    monkeypatch.setattr(
        settings, "payhere_merchant_secret", "test-secret"
    )
    monkeypatch.setattr(settings, "payhere_sandbox", True)
    monkeypatch.setattr(
        settings, "frontend_base_url", "http://127.0.0.1:5173"
    )
    monkeypatch.setattr(
        settings, "backend_public_url", "http://127.0.0.1:8005"
    )

    order = _create_online_order(
        client, customer_auth, product, order_payload
    )
    session = client.post(
        f"/payments/orders/{order['id']}/session",
        headers=customer_auth["headers"],
    )
    assert session.status_code == 200, session.text
    data = session.json()
    assert data["provider"] == "payhere"
    assert data["action_url"] == (
        "https://sandbox.payhere.lk/pay/checkout"
    )
    assert "merchant_secret" not in data["fields"]
    assert data["fields"]["merchant_id"] == "test-merchant"
    assert data["fields"]["order_id"] == data["reference"]
    assert data["fields"]["amount"] == f"{order['total']:.2f}"
    assert data["fields"]["currency"] == "LKR"
    assert data["fields"]["notify_url"].endswith(
        "/payments/payhere/notify"
    )

    secret_hash = _secret_hash("test-secret")
    expected_hash = _signature(
        "test-merchant",
        data["reference"],
        f"{order['total']:.2f}",
        "LKR",
        secret_hash,
    )
    assert data["fields"]["hash"] == expected_hash

    amount = f"{order['total']:.2f}"
    notify_signature = _signature(
        "test-merchant",
        data["reference"],
        amount,
        "LKR",
        "2",
        secret_hash,
    )
    notification = client.post(
        "/payments/payhere/notify",
        data={
            "merchant_id": "test-merchant",
            "order_id": data["reference"],
            "payment_id": "payhere-payment-1",
            "payhere_amount": amount,
            "payhere_currency": "LKR",
            "status_code": "2",
            "md5sig": notify_signature,
        },
    )
    assert notification.status_code == 200, notification.text
    assert notification.json() == {"status": "ok"}

    paid_order = client.get(
        f"/orders/{order['id']}",
        headers=customer_auth["headers"],
    )
    assert paid_order.json()["payment_status"] == "paid"

    duplicate = client.post(
        "/payments/payhere/notify",
        data={
            "merchant_id": "test-merchant",
            "order_id": data["reference"],
            "payment_id": "payhere-payment-1",
            "payhere_amount": amount,
            "payhere_currency": "LKR",
            "status_code": "2",
            "md5sig": notify_signature,
        },
    )
    assert duplicate.status_code == 200
    assert duplicate.json() == {"status": "ok"}


def test_payhere_rejects_invalid_signature_and_amount(
    client, customer_auth, product, order_payload, monkeypatch
):
    monkeypatch.setattr(settings, "payment_provider", "payhere")
    monkeypatch.setattr(settings, "payhere_merchant_id", "test-merchant")
    monkeypatch.setattr(
        settings, "payhere_merchant_secret", "test-secret"
    )

    order = _create_online_order(
        client, customer_auth, product, order_payload
    )
    session = client.post(
        f"/payments/orders/{order['id']}/session",
        headers=customer_auth["headers"],
    ).json()
    secret_hash = _secret_hash("test-secret")
    amount = f"{order['total']:.2f}"

    invalid_signature = client.post(
        "/payments/payhere/notify",
        data={
            "merchant_id": "test-merchant",
            "order_id": session["reference"],
            "payhere_amount": amount,
            "payhere_currency": "LKR",
            "status_code": "2",
            "md5sig": "BAD",
        },
    )
    assert invalid_signature.status_code == 400

    wrong_amount = "1.00"
    valid_but_wrong_amount = client.post(
        "/payments/payhere/notify",
        data={
            "merchant_id": "test-merchant",
            "order_id": session["reference"],
            "payhere_amount": wrong_amount,
            "payhere_currency": "LKR",
            "status_code": "2",
            "md5sig": _signature(
                "test-merchant",
                session["reference"],
                wrong_amount,
                "LKR",
                "2",
                secret_hash,
            ),
        },
    )
    assert valid_but_wrong_amount.status_code == 400

    order_after = client.get(
        f"/orders/{order['id']}",
        headers=customer_auth["headers"],
    )
    assert order_after.json()["payment_status"] == "pending"


def test_payhere_failed_payment_can_be_retried(
    client, customer_auth, product, order_payload, monkeypatch
):
    monkeypatch.setattr(settings, "payment_provider", "payhere")
    monkeypatch.setattr(settings, "payhere_merchant_id", "test-merchant")
    monkeypatch.setattr(
        settings, "payhere_merchant_secret", "test-secret"
    )

    order = _create_online_order(
        client, customer_auth, product, order_payload
    )
    secret_hash = _secret_hash("test-secret")
    amount = f"{order['total']:.2f}"

    def notify(reference, status_code):
        return client.post(
            "/payments/payhere/notify",
            data={
                "merchant_id": "test-merchant",
                "order_id": reference,
                "payhere_amount": amount,
                "payhere_currency": "LKR",
                "status_code": status_code,
                "md5sig": _signature(
                    "test-merchant",
                    reference,
                    amount,
                    "LKR",
                    status_code,
                    secret_hash,
                ),
            },
        )

    first_session = client.post(
        f"/payments/orders/{order['id']}/session",
        headers=customer_auth["headers"],
    ).json()
    failed = notify(first_session["reference"], "-2")
    assert failed.status_code == 200

    failed_order = client.get(
        f"/orders/{order['id']}",
        headers=customer_auth["headers"],
    )
    assert failed_order.json()["payment_status"] == "failed"

    retry_session = client.post(
        f"/payments/orders/{order['id']}/session",
        headers=customer_auth["headers"],
    )
    assert retry_session.status_code == 200
    assert retry_session.json()["reference"] != first_session["reference"]

    paid = notify(retry_session.json()["reference"], "2")
    assert paid.status_code == 200

    paid_order = client.get(
        f"/orders/{order['id']}",
        headers=customer_auth["headers"],
    )
    assert paid_order.json()["payment_status"] == "paid"


def test_paid_order_is_not_downgraded_when_cancelled(
    client, admin_auth, customer_auth, product, order_payload
):
    order = _create_online_order(
        client, customer_auth, product, order_payload
    )
    client.post(
        f"/payments/orders/{order['id']}/session",
        headers=customer_auth["headers"],
    )
    client.post(
        f"/payments/orders/{order['id']}/mock-complete",
        headers=customer_auth["headers"],
    )

    cancelled = client.patch(
        f"/admin/orders/{order['id']}/status",
        headers=admin_auth["headers"],
        json={"status": "cancelled"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["payment_status"] == "paid"


def test_chargeback_after_payment_and_duplicate_notifications(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
    monkeypatch,
):
    _configure_payhere(monkeypatch)
    order = _create_online_order(
        client, customer_auth, product, order_payload
    )
    session = client.post(
        f"/payments/orders/{order['id']}/session",
        headers=customer_auth["headers"],
    ).json()
    amount = f"{order['total']:.2f}"

    paid = _payhere_notify(
        client, session["reference"], amount, "2"
    )
    assert paid.status_code == 200

    chargeback = _payhere_notify(
        client, session["reference"], amount, "-3"
    )
    assert chargeback.status_code == 200
    assert chargeback.json() == {"status": "ok"}

    order_after = client.get(
        f"/orders/{order['id']}",
        headers=customer_auth["headers"],
    ).json()
    assert order_after["payment_status"] == "chargedback"

    payments = client.get(
        f"/admin/orders/{order['id']}/payments",
        headers=admin_auth["headers"],
    ).json()
    payment = payments[0]
    assert payment["status"] == "chargedback"
    assert payment["paid_at"] is not None
    assert payment["provider_payment_id"] == "payhere-payment-1"
    event_statuses = [
        event["status"] for event in payment["events"]
    ]
    assert event_statuses == ["pending", "paid", "chargedback"]

    duplicate = _payhere_notify(
        client, session["reference"], amount, "-3"
    )
    assert duplicate.status_code == 200
    assert duplicate.json() == {"status": "ok"}

    payments_after_duplicate = client.get(
        f"/admin/orders/{order['id']}/payments",
        headers=admin_auth["headers"],
    ).json()
    assert len(payments_after_duplicate[0]["events"]) == 3

    late_failure = _payhere_notify(
        client, session["reference"], amount, "-2"
    )
    assert late_failure.status_code == 200
    assert late_failure.json() == {"status": "ignored"}

    final_order = client.get(
        f"/orders/{order['id']}",
        headers=customer_auth["headers"],
    ).json()
    assert final_order["payment_status"] == "chargedback"

    retry_after_chargeback = client.post(
        f"/payments/orders/{order['id']}/session",
        headers=customer_auth["headers"],
    )
    assert retry_after_chargeback.status_code == 409


def test_admin_payment_history_and_manual_reconciliation(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
    monkeypatch,
):
    order = _create_online_order(
        client, customer_auth, product, order_payload
    )
    session = client.post(
        f"/payments/orders/{order['id']}/session",
        headers=customer_auth["headers"],
    ).json()

    anonymous = client.get(
        f"/admin/orders/{order['id']}/payments"
    )
    customer = client.get(
        f"/admin/orders/{order['id']}/payments",
        headers=customer_auth["headers"],
    )
    history = client.get(
        f"/admin/orders/{order['id']}/payments",
        headers=admin_auth["headers"],
    )
    assert anonymous.status_code == 401
    assert customer.status_code == 403
    assert history.status_code == 200
    payment = history.json()[0]
    assert payment["reference"] == session["reference"]
    assert payment["status"] == "pending"
    assert payment["events"][0]["source"] == "session"

    calls = []
    monkeypatch.setattr(
        "app.routers.admin_orders.send_payment_confirmation",
        lambda *args: calls.append(args),
    )

    paid = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/reconcile",
        headers=admin_auth["headers"],
        json={
            "status": "paid",
            "provider_payment_id": "manual-txn-1",
            "note": "Verified in the PayHere dashboard.",
        },
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "paid"
    assert paid.json()["events"][-1]["source"] == "manual"
    assert paid.json()["events"][-1]["actor_user_id"] is not None
    assert len(calls) == 1

    paid_order = client.get(
        f"/orders/{order['id']}",
        headers=customer_auth["headers"],
    ).json()
    assert paid_order["payment_status"] == "paid"

    downgrade = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/reconcile",
        headers=admin_auth["headers"],
        json={
            "status": "failed",
            "note": "Should be rejected.",
        },
    )
    assert downgrade.status_code == 409

    missing_transaction_id = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/reconcile",
        headers=admin_auth["headers"],
        json={
            "status": "paid",
            "note": "Missing transaction ID.",
        },
    )
    assert missing_transaction_id.status_code == 422

    chargedback = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/reconcile",
        headers=admin_auth["headers"],
        json={
            "status": "chargedback",
            "provider_payment_id": "manual-cb-1",
            "note": "Chargeback confirmed in PayHere.",
        },
    )
    assert chargedback.status_code == 200
    assert chargedback.json()["status"] == "chargedback"

    final_order = client.get(
        f"/orders/{order['id']}",
        headers=customer_auth["headers"],
    ).json()
    assert final_order["payment_status"] == "chargedback"

    retry_after_chargeback = client.post(
        f"/payments/orders/{order['id']}/session",
        headers=customer_auth["headers"],
    )
    assert retry_after_chargeback.status_code == 409

    customer_reconcile = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/reconcile",
        headers=customer_auth["headers"],
        json={
            "status": "paid",
            "provider_payment_id": "customer-forged",
            "note": "Should not work.",
        },
    )
    assert customer_reconcile.status_code == 403


def test_online_unpaid_order_cannot_be_delivered(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
):
    order = _create_online_order(
        client, customer_auth, product, order_payload
    )
    session = client.post(
        f"/payments/orders/{order['id']}/session",
        headers=customer_auth["headers"],
    )
    assert session.status_code == 200

    for status in ("confirmed", "shipped"):
        response = client.patch(
            f"/admin/orders/{order['id']}/status",
            headers=admin_auth["headers"],
            json={"status": status},
        )
        assert response.status_code == 200

    blocked = client.patch(
        f"/admin/orders/{order['id']}/status",
        headers=admin_auth["headers"],
        json={"status": "delivered"},
    )
    assert blocked.status_code == 409
    assert "must be paid" in blocked.json()["detail"]

    delivered = client.get(
        f"/admin/orders/{order['id']}",
        headers=admin_auth["headers"],
    ).json()
    assert delivered["status"] == "shipped"
    assert delivered["payment_status"] == "pending"

    payments = client.get(
        f"/admin/orders/{order['id']}/payments",
        headers=admin_auth["headers"],
    ).json()
    failed = client.post(
        f"/admin/orders/{order['id']}/payments/{payments[0]['id']}/reconcile",
        headers=admin_auth["headers"],
        json={
            "status": "failed",
            "note": "Provider reports a failed payment.",
        },
    )
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"

    blocked_failed = client.patch(
        f"/admin/orders/{order['id']}/status",
        headers=admin_auth["headers"],
        json={"status": "delivered"},
    )
    assert blocked_failed.status_code == 409


def test_online_paid_order_can_be_delivered(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
):
    order = _create_online_order(
        client, customer_auth, product, order_payload
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

    for status in ("confirmed", "shipped", "delivered"):
        response = client.patch(
            f"/admin/orders/{order['id']}/status",
            headers=admin_auth["headers"],
            json={"status": status},
        )
        assert response.status_code == 200, response.text

    assert response.json()["payment_status"] == "paid"


def test_cod_order_can_be_delivered_and_becomes_paid(
    client, admin_auth, customer_auth, product, order_payload
):
    _add_to_cart(client, customer_auth["headers"], product, 1)
    order = client.post(
        "/orders",
        headers=customer_auth["headers"],
        json=order_payload,
    ).json()

    for status in ("confirmed", "shipped", "delivered"):
        response = client.patch(
            f"/admin/orders/{order['id']}/status",
            headers=admin_auth["headers"],
            json={"status": status},
        )
        assert response.status_code == 200, response.text

    assert response.json()["payment_status"] == "paid"


def test_mock_mode_is_disabled_in_production(monkeypatch):
    production_mock = Settings(
        app_env="production",
        payment_provider="mock",
        payment_mock_enabled=True,
    )

    with pytest.raises(RuntimeError):
        validate_payment_security(production_mock)

    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "payment_provider", "mock")
    monkeypatch.setattr(settings, "payment_mock_enabled", True)

    from app.services.payments import get_config

    config = get_config()
    assert config.online_enabled is False
    assert config.mock_enabled is False


def test_mock_completion_is_unavailable_with_payhere(
    client,
    customer_auth,
    product,
    order_payload,
    monkeypatch,
):
    order = _create_online_order(
        client, customer_auth, product, order_payload
    )
    _configure_payhere(monkeypatch)

    response = client.post(
        f"/payments/orders/{order['id']}/mock-complete",
        headers=customer_auth["headers"],
    )
    assert response.status_code == 404


def test_payhere_payment_confirmation_email_is_sent_once(
    client,
    customer_auth,
    product,
    order_payload,
    monkeypatch,
):
    _configure_payhere(monkeypatch)
    calls = []
    monkeypatch.setattr(
        "app.routers.payments.send_payment_confirmation",
        lambda *args: calls.append(args),
    )

    order = _create_online_order(
        client, customer_auth, product, order_payload
    )
    session = client.post(
        f"/payments/orders/{order['id']}/session",
        headers=customer_auth["headers"],
    ).json()
    assert calls == []

    amount = f"{order['total']:.2f}"
    first = _payhere_notify(
        client, session["reference"], amount, "2"
    )
    assert first.status_code == 200
    assert len(calls) == 1
    assert calls[0][0] == customer_auth["user"]["email"]
    assert calls[0][1] == order["id"]
    assert calls[0][4] == session["reference"]

    duplicate = _payhere_notify(
        client, session["reference"], amount, "2"
    )
    assert duplicate.status_code == 200
    assert len(calls) == 1


def test_delayed_payhere_success_after_expiry_does_not_restore_stock(
    client,
    customer_auth,
    product,
    order_payload,
    monkeypatch,
):
    from datetime import timedelta

    from app.database import SessionLocal
    from app.models import Order, ProductVariant
    from app.models.common import utcnow
    from app.services.stock import expire_unpaid_online_orders

    _configure_payhere(monkeypatch)
    order = _create_online_order(
        client, customer_auth, product, order_payload
    )
    session = client.post(
        f"/payments/orders/{order['id']}/session",
        headers=customer_auth["headers"],
    ).json()

    with SessionLocal() as db:
        stored = db.get(Order, order["id"])
        stored.reservation_expires_at = utcnow() - timedelta(
            minutes=1
        )
        db.commit()
        assert expire_unpaid_online_orders(db) == 1

    amount = f"{order['total']:.2f}"
    delayed = _payhere_notify(
        client, session["reference"], amount, "2"
    )
    assert delayed.status_code == 200
    assert delayed.json() == {"status": "ok"}

    current = client.get(
        f"/orders/{order['id']}",
        headers=customer_auth["headers"],
    ).json()
    assert current["status"] == "cancelled"
    assert current["payment_status"] == "paid"
    assert current["stock_released_at"] is not None

    with SessionLocal() as db:
        variant = db.get(
            ProductVariant, product["variants"][0]["id"]
        )
        assert variant.stock == 8


def test_chargedback_delivered_order_is_excluded_from_revenue(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
):
    order = _create_online_order(
        client, customer_auth, product, order_payload
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

    for status in ("confirmed", "shipped", "delivered"):
        response = client.patch(
            f"/admin/orders/{order['id']}/status",
            headers=admin_auth["headers"],
            json={"status": status},
        )
        assert response.status_code == 200

    payments = client.get(
        f"/admin/orders/{order['id']}/payments",
        headers=admin_auth["headers"],
    ).json()
    chargedback = client.post(
        f"/admin/orders/{order['id']}/payments/{payments[0]['id']}/reconcile",
        headers=admin_auth["headers"],
        json={
            "status": "chargedback",
            "provider_payment_id": "manual-cb-revenue",
            "note": "Chargeback verified for revenue test.",
        },
    )
    assert chargedback.status_code == 200
    assert chargedback.json()["status"] == "chargedback"

    stats = client.get(
        "/admin/stats", headers=admin_auth["headers"]
    ).json()
    assert stats["delivered_orders"] == 1
    assert stats["revenue"] == 0


def test_order_creation_cannot_forge_payment_status(
    client, customer_auth, product, order_payload
):
    _add_to_cart(client, customer_auth["headers"], product, 1)
    response = client.post(
        "/orders",
        headers=customer_auth["headers"],
        json={**order_payload, "payment_status": "paid"},
    )
    assert response.status_code == 422
