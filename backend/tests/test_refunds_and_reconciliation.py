from decimal import Decimal

from app.config import settings
from app.models import Payment
from app.services.payhere_api import PayHereApiError, ProviderPayment


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


def _session_and_payment(client, customer_auth, admin_auth, order):
    session = client.post(
        f"/payments/orders/{order['id']}/session",
        headers=customer_auth["headers"],
    )
    assert session.status_code == 200, session.text
    payments = client.get(
        f"/admin/orders/{order['id']}/payments",
        headers=admin_auth["headers"],
    )
    assert payments.status_code == 200
    return session.json(), payments.json()[0]


def _complete_mock(client, customer_auth, order):
    response = client.post(
        f"/payments/orders/{order['id']}/mock-complete",
        headers=customer_auth["headers"],
    )
    assert response.status_code == 200, response.text


def test_provider_reconciliation_mock_success_and_idempotency(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
    monkeypatch,
):
    email_calls = []
    monkeypatch.setattr(
        "app.routers.admin_orders.send_payment_confirmation",
        lambda *args: email_calls.append(args),
    )
    order = _create_online_order(
        client, customer_auth, product, order_payload
    )
    session, payment = _session_and_payment(
        client, customer_auth, admin_auth, order
    )

    anonymous = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/reconcile-provider"
    )
    customer = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/reconcile-provider",
        headers=customer_auth["headers"],
    )
    reconciled = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/reconcile-provider",
        headers=admin_auth["headers"],
    )
    assert anonymous.status_code == 401
    assert customer.status_code == 403
    assert reconciled.status_code == 200, reconciled.text
    assert reconciled.json()["status"] == "paid"
    assert reconciled.json()["provider_payment_id"].startswith("mock-")
    assert reconciled.json()["events"][-1]["source"] == "payhere_api"
    assert len(email_calls) == 1

    events_before = len(reconciled.json()["events"])
    duplicate = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/reconcile-provider",
        headers=admin_auth["headers"],
    )
    assert duplicate.status_code == 200
    assert len(duplicate.json()["events"]) == events_before
    assert len(email_calls) == 1

    paid_order = client.get(
        f"/orders/{order['id']}",
        headers=customer_auth["headers"],
    ).json()
    assert paid_order["payment_status"] == "paid"
    assert session["reference"] == payment["reference"]


def test_provider_reconciliation_chargeback_and_refund_states(
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
    _, payment = _session_and_payment(
        client, customer_auth, admin_auth, order
    )
    _complete_mock(client, customer_auth, order)
    amount = Decimal(order["total"])
    currency = "LKR"

    monkeypatch.setattr(
        "app.services.payments.payhere_api.lookup_payment",
        lambda reference, *, expected_amount, currency: ProviderPayment(
            payment_id="payhere-cb-1",
            order_id=reference,
            status="CHARGEBACKED",
            amount=Decimal(expected_amount),
            currency=currency,
        ),
    )
    chargedback = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/reconcile-provider",
        headers=admin_auth["headers"],
    )
    assert chargedback.status_code == 200, chargedback.text
    assert chargedback.json()["status"] == "chargedback"

    order_after = client.get(
        f"/orders/{order['id']}",
        headers=customer_auth["headers"],
    ).json()
    assert order_after["payment_status"] == "chargedback"

    refunded_order = _create_online_order(
        client,
        customer_auth,
        product,
        {
            **order_payload,
            "contact_name": "Refunded Customer",
        },
    )
    _, refunded_payment = _session_and_payment(
        client, customer_auth, admin_auth, refunded_order
    )
    _complete_mock(client, customer_auth, refunded_order)

    monkeypatch.setattr(
        "app.services.payments.payhere_api.lookup_payment",
        lambda reference, *, expected_amount, currency: ProviderPayment(
            payment_id="payhere-ref-1",
            order_id=reference,
            status="REFUNDED",
            amount=Decimal(expected_amount),
            currency=currency,
        ),
    )
    refunded = client.post(
        f"/admin/orders/{refunded_order['id']}/payments/{refunded_payment['id']}/reconcile-provider",
        headers=admin_auth["headers"],
    )
    assert refunded.status_code == 200, refunded.text
    assert refunded.json()["status"] == "refunded"
    assert len(refunded.json()["refunds"]) == 1
    assert refunded.json()["refunds"][0]["status"] == "refunded"

    refunded_customer_order = client.get(
        f"/orders/{refunded_order['id']}",
        headers=customer_auth["headers"],
    ).json()
    assert refunded_customer_order["payment_status"] == "refunded"

    # A terminal chargedback and a provider refund conflict must not silently
    # overwrite each other.
    monkeypatch.setattr(
        "app.services.payments.payhere_api.lookup_payment",
        lambda reference, *, expected_amount, currency: ProviderPayment(
            payment_id="payhere-ref-conflict",
            order_id=reference,
            status="REFUNDED",
            amount=amount,
            currency=currency,
        ),
    )
    conflict = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/reconcile-provider",
        headers=admin_auth["headers"],
    )
    assert conflict.status_code == 409


def test_provider_reconciliation_rejects_mismatched_amount(
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
    _, payment = _session_and_payment(
        client, customer_auth, admin_auth, order
    )

    monkeypatch.setattr(
        "app.services.payments.payhere_api.lookup_payment",
        lambda reference, *, expected_amount, currency: ProviderPayment(
            payment_id="payhere-mismatch",
            order_id=reference,
            status="RECEIVED",
            amount=Decimal(expected_amount + 1),
            currency=currency,
        ),
    )
    response = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/reconcile-provider",
        headers=admin_auth["headers"],
    )
    assert response.status_code == 502

    current = client.get(
        f"/orders/{order['id']}",
        headers=customer_auth["headers"],
    ).json()
    assert current["payment_status"] == "pending"


def test_provider_reconciliation_disabled_returns_503(
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
    _, payment = _session_and_payment(
        client, customer_auth, admin_auth, order
    )
    monkeypatch.setattr(settings, "payment_provider", "disabled")

    response = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/reconcile-provider",
        headers=admin_auth["headers"],
    )
    assert response.status_code == 503


def test_manual_refund_records_and_over_refund_protection(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
):
    order = _create_online_order(
        client, customer_auth, product, order_payload
    )
    _, payment = _session_and_payment(
        client, customer_auth, admin_auth, order
    )
    _complete_mock(client, customer_auth, order)

    payload = {
        "kind": "refund",
        "amount": 100,
        "reason": "Customer requested a partial refund.",
        "notes": "Manual test refund.",
    }
    customer_create = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/refunds",
        headers=customer_auth["headers"],
        json=payload,
    )
    assert customer_create.status_code == 403

    first = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/refunds",
        headers=admin_auth["headers"],
        json=payload,
    )
    assert first.status_code == 201, first.text
    assert first.json()["status"] == "pending"
    assert first.json()["provider"] == "manual"

    second = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/refunds",
        headers=admin_auth["headers"],
        json={**payload, "amount": 100},
    )
    assert second.status_code == 201

    too_much = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/refunds",
        headers=admin_auth["headers"],
        json={**payload, "amount": order["total"]},
    )
    assert too_much.status_code == 400

    customer_list = client.get(
        f"/admin/orders/{order['id']}/refunds",
        headers=customer_auth["headers"],
    )
    assert customer_list.status_code == 403

    refunds = client.get(
        f"/admin/orders/{order['id']}/refunds",
        headers=admin_auth["headers"],
    )
    assert refunds.status_code == 200
    assert len(refunds.json()) == 2

    completed = client.patch(
        f"/admin/orders/{order['id']}/refunds/{first.json()['id']}",
        headers=admin_auth["headers"],
        json={
            "status": "refunded",
            "note": "Refunded in cash.",
        },
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "refunded"

    order_after_partial = client.get(
        f"/orders/{order['id']}",
        headers=customer_auth["headers"],
    ).json()
    assert order_after_partial["payment_status"] == "paid"

    history = client.get(
        f"/admin/orders/{order['id']}/payments",
        headers=admin_auth["headers"],
    ).json()
    assert len(history[0]["refunds"]) == 2
    assert any(
        event["status"] == "refund_partial"
        for event in history[0]["events"]
    )


def test_full_provider_refund_updates_payment_and_order(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
):
    order = _create_online_order(
        client, customer_auth, product, order_payload
    )
    _, payment = _session_and_payment(
        client, customer_auth, admin_auth, order
    )
    _complete_mock(client, customer_auth, order)

    response = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/refunds",
        headers=admin_auth["headers"],
        json={
            "kind": "return",
            "amount": order["total"],
            "reason": "Item returned in original condition.",
            "process_with_provider": True,
        },
    )
    assert response.status_code == 201, response.text
    refund = response.json()
    assert refund["status"] == "refunded"
    assert refund["provider"] == "mock"
    assert refund["provider_refund_id"].startswith("mock-refund-")

    current_order = client.get(
        f"/orders/{order['id']}",
        headers=customer_auth["headers"],
    ).json()
    assert current_order["payment_status"] == "refunded"

    create_session = client.post(
        f"/payments/orders/{order['id']}/session",
        headers=customer_auth["headers"],
    )
    assert create_session.status_code == 409


def test_provider_refund_failure_preserves_failed_record(
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
    _, payment = _session_and_payment(
        client, customer_auth, admin_auth, order
    )
    _complete_mock(client, customer_auth, order)

    def fail_refund(*args, **kwargs):
        raise PayHereApiError("Provider refund unavailable.")

    monkeypatch.setattr(
        "app.services.refunds.payhere_api.refund_payment",
        fail_refund,
    )

    response = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/refunds",
        headers=admin_auth["headers"],
        json={
            "kind": "refund",
            "amount": 100,
            "reason": "Provider refund failure test.",
            "process_with_provider": True,
        },
    )
    assert response.status_code == 502

    refunds = client.get(
        f"/admin/orders/{order['id']}/refunds",
        headers=admin_auth["headers"],
    ).json()
    assert len(refunds) == 1
    assert refunds[0]["status"] == "failed"

    current = client.get(
        f"/orders/{order['id']}",
        headers=customer_auth["headers"],
    ).json()
    assert current["payment_status"] == "paid"


def test_refund_requires_paid_payment(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
):
    order = _create_online_order(
        client, customer_auth, product, order_payload
    )
    _, payment = _session_and_payment(
        client, customer_auth, admin_auth, order
    )

    response = client.post(
        f"/admin/orders/{order['id']}/payments/{payment['id']}/refunds",
        headers=admin_auth["headers"],
        json={
            "kind": "refund",
            "amount": 100,
            "reason": "Payment is still pending.",
        },
    )
    assert response.status_code == 409
