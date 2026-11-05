from urllib.parse import parse_qs, urlparse

import app.routers.auth as auth_router
from app.config import settings


def _token_from_url(url: str) -> str:
    return parse_qs(urlparse(url).query)["token"][0]


def _register(
    client,
    email="account@furzy.dev",
    password="AccountPass123!",
):
    response = client.post(
        "/auth/register",
        json={
            "name": "Account Customer",
            "email": email,
            "password": password,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _login(client, email, password):
    return client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )


def test_auth_config_reports_available_flows(client, monkeypatch):
    response = client.get("/auth/config")
    assert response.status_code == 200
    assert response.json() == {
        "email_verification_required": False,
        "email_verification_available": False,
        "password_reset_available": False,
    }

    monkeypatch.setattr(settings, "smtp_host", "smtp.test")
    monkeypatch.setattr(
        settings, "smtp_from_email", "no-reply@furzy.dev"
    )
    monkeypatch.setattr(
        settings, "email_verification_required", True
    )

    configured = client.get("/auth/config").json()
    assert configured["email_verification_required"] is True
    assert configured["email_verification_available"] is True
    assert configured["password_reset_available"] is True


def test_email_verification_flow(client, monkeypatch):
    sent = []
    monkeypatch.setattr(settings, "smtp_host", "smtp.test")
    monkeypatch.setattr(
        settings, "smtp_from_email", "no-reply@furzy.dev"
    )
    monkeypatch.setattr(
        settings, "email_verification_required", True
    )
    monkeypatch.setattr(
        auth_router,
        "send_email_verification",
        lambda *args: sent.append(args),
    )

    registered = _register(client)
    assert registered["user"]["email_verified"] is False
    assert len(sent) == 1

    blocked = _login(
        client, "account@furzy.dev", "AccountPass123!"
    )
    assert blocked.status_code == 403
    assert "verify your email" in blocked.json()["detail"].lower()

    first_token = _token_from_url(sent[0][2])

    resent = client.post(
        "/auth/verify-email/resend",
        json={"email": "account@furzy.dev"},
    )
    assert resent.status_code == 202
    assert len(sent) == 2
    second_token = _token_from_url(sent[1][2])

    stale = client.post(
        "/auth/verify-email", json={"token": first_token}
    )
    assert stale.status_code == 400

    verified = client.post(
        "/auth/verify-email", json={"token": second_token}
    )
    assert verified.status_code == 200

    allowed = _login(
        client, "account@furzy.dev", "AccountPass123!"
    )
    assert allowed.status_code == 200
    assert allowed.json()["user"]["email_verified"] is True

    reused = client.post(
        "/auth/verify-email", json={"token": second_token}
    )
    assert reused.status_code == 400


def test_resend_verification_hides_unknown_email(client):
    response = client.post(
        "/auth/verify-email/resend",
        json={"email": "missing@furzy.dev"},
    )
    assert response.status_code == 202
    assert "sent" in response.json()["message"]


def test_password_reset_rotates_password_and_tokens(
    client, monkeypatch
):
    registered = _register(
        client,
        email="reset@furzy.dev",
        password="OldPass123!",
    )
    old_access = registered["access_token"]

    sent = []
    monkeypatch.setattr(settings, "smtp_host", "smtp.test")
    monkeypatch.setattr(
        settings, "smtp_from_email", "no-reply@furzy.dev"
    )
    monkeypatch.setattr(
        auth_router,
        "send_password_reset",
        lambda *args: sent.append(args),
    )

    requested = client.post(
        "/auth/password/forgot",
        json={"email": "reset@furzy.dev"},
    )
    assert requested.status_code == 202
    assert len(sent) == 1
    token = _token_from_url(sent[0][2])

    reset = client.post(
        "/auth/password/reset",
        json={"token": token, "new_password": "NewPass123!"},
    )
    assert reset.status_code == 200, reset.text

    assert _login(
        client, "reset@furzy.dev", "OldPass123!"
    ).status_code == 401
    assert _login(
        client, "reset@furzy.dev", "NewPass123!"
    ).status_code == 200

    # Access tokens issued before the reset are no longer valid.
    me = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {old_access}"},
    )
    assert me.status_code == 401

    reused = client.post(
        "/auth/password/reset",
        json={"token": token, "new_password": "AnotherPass123!"},
    )
    assert reused.status_code == 400


def test_password_forgot_is_generic_and_rate_limited(
    client, monkeypatch
):
    sent = []
    monkeypatch.setattr(settings, "smtp_host", "smtp.test")
    monkeypatch.setattr(
        settings, "smtp_from_email", "no-reply@furzy.dev"
    )
    monkeypatch.setattr(
        auth_router,
        "send_password_reset",
        lambda *args: sent.append(args),
    )

    missing = client.post(
        "/auth/password/forgot",
        json={"email": "nobody@furzy.dev"},
    )
    assert missing.status_code == 202
    assert sent == []

    for _ in range(2):
        assert (
            client.post(
                "/auth/password/forgot",
                json={"email": "nobody@furzy.dev"},
            ).status_code
            == 202
        )

    limited = client.post(
        "/auth/password/forgot",
        json={"email": "nobody@furzy.dev"},
    )
    assert limited.status_code == 429
    assert limited.headers["Retry-After"]


def test_invalid_and_expired_account_tokens_are_rejected(client):
    invalid = client.post(
        "/auth/password/reset",
        json={
            "token": "x" * 40,
            "new_password": "WhateverPass123!",
        },
    )
    assert invalid.status_code == 400

    invalid_verify = client.post(
        "/auth/verify-email", json={"token": "y" * 40}
    )
    assert invalid_verify.status_code == 400
