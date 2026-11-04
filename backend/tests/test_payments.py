import hashlib

from app.config import settings


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
