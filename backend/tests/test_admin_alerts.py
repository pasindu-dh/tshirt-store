from app.config import settings
from app.services import email as email_service
from app.services import notifications

from app.database import SessionLocal


def _add_to_cart(client, headers, product):
    response = client.post(
        "/cart/items",
        headers=headers,
        json={
            "variant_id": product["variants"][0]["id"],
            "quantity": 1,
        },
    )
    assert response.status_code == 200, response.text


def test_admin_alert_recipients_default_and_configured(
    client, admin_auth, monkeypatch
):
    with SessionLocal() as db:
        assert notifications.admin_alert_recipients(db) == [
            "admin@furzy.dev"
        ]

        monkeypatch.setattr(
            settings,
            "admin_alert_emails",
            "ops@furzy.dev, alerts@furzy.dev",
        )
        assert notifications.admin_alert_recipients(db) == [
            "ops@furzy.dev",
            "alerts@furzy.dev",
        ]


def test_new_order_sends_admin_alert_email(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
    monkeypatch,
):
    sent = []
    monkeypatch.setattr(settings, "smtp_host", "smtp.test")
    monkeypatch.setattr(
        settings, "smtp_from_email", "no-reply@furzy.dev"
    )
    monkeypatch.setattr(
        settings,
        "admin_alert_emails",
        "ops@furzy.dev",
    )
    monkeypatch.setattr(
        notifications,
        "send_admin_alert",
        lambda *args: sent.append(args),
    )

    _add_to_cart(client, customer_auth["headers"], product)
    response = client.post(
        "/orders",
        headers=customer_auth["headers"],
        json=order_payload,
    )
    assert response.status_code == 201, response.text
    order_id = response.json()["id"]

    notifications.flush_admin_alerts()

    assert len(sent) == 1
    recipients, title, message, link = sent[0]
    assert recipients == ["ops@furzy.dev"]
    assert title == f"New order #{order_id}"
    assert "LKR" in message
    assert link == f"/admin/orders/{order_id}"


def test_admin_alert_email_can_be_disabled(
    client,
    admin_auth,
    customer_auth,
    product,
    order_payload,
    monkeypatch,
):
    sent = []
    monkeypatch.setattr(settings, "smtp_host", "smtp.test")
    monkeypatch.setattr(
        settings, "smtp_from_email", "no-reply@furzy.dev"
    )
    monkeypatch.setattr(
        settings, "admin_email_alerts_enabled", False
    )
    monkeypatch.setattr(
        notifications,
        "send_admin_alert",
        lambda *args: sent.append(args),
    )

    _add_to_cart(client, customer_auth["headers"], product)
    response = client.post(
        "/orders",
        headers=customer_auth["headers"],
        json=order_payload,
    )
    assert response.status_code == 201

    notifications.flush_admin_alerts()
    assert sent == []


def test_admin_alert_email_body_links_to_admin_panel(
    monkeypatch,
):
    sent = []
    monkeypatch.setattr(
        email_service,
        "_send_email",
        lambda to, subject, body: (
            sent.append((to, subject, body)) or True
        ),
    )

    delivered = email_service.send_admin_alert(
        ["one@furzy.dev", "two@furzy.dev"],
        "Low stock: Test Tee",
        "Only 2 remain.",
        "/admin/inventory",
    )

    assert delivered == 2
    assert [item[0] for item in sent] == [
        "one@furzy.dev",
        "two@furzy.dev",
    ]
    assert sent[0][1] == "[FURZY admin] Low stock: Test Tee"
    assert sent[0][2].count("http") == 1
    assert "/admin/inventory" in sent[0][2]
