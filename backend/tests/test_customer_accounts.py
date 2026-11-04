CUSTOMER_PASSWORD = "CustomerPass123!"


def _login(client, email, password=CUSTOMER_PASSWORD):
    return client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )


def _set_status(client, admin_auth, customer_id, is_active):
    return client.patch(
        f"/admin/customers/{customer_id}/status",
        headers=admin_auth["headers"],
        json={"is_active": is_active},
    )


def test_admin_can_deactivate_and_reactivate_customer(
    client,
    admin_auth,
    customer_auth,
):
    customer = customer_auth["user"]
    listing = client.get(
        "/admin/customers",
        headers=admin_auth["headers"],
    )
    assert listing.status_code == 200
    listed = next(
        item
        for item in listing.json()
        if item["id"] == customer["id"]
    )
    assert listed["is_active"] is True

    deactivated = _set_status(
        client, admin_auth, customer["id"], False
    )
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["is_active"] is False

    detail = client.get(
        f"/admin/customers/{customer['id']}",
        headers=admin_auth["headers"],
    )
    assert detail.status_code == 200
    assert detail.json()["is_active"] is False

    login = _login(client, customer["email"])
    assert login.status_code == 403
    assert "deactivated" in login.json()["detail"].lower()

    me = client.get(
        "/auth/me", headers=customer_auth["headers"]
    )
    refreshed = client.post(
        "/auth/refresh",
        json={"refresh_token": customer_auth["refresh_token"]},
    )
    assert me.status_code == 401
    assert refreshed.status_code == 401

    reactivated = _set_status(
        client, admin_auth, customer["id"], True
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["is_active"] is True

    login = _login(client, customer["email"])
    assert login.status_code == 200
    assert login.json()["user"]["is_active"] is True


def test_customer_status_access_controls_and_validation(
    client,
    admin_auth,
    customer_auth,
):
    customer = customer_auth["user"]

    customer_attempt = _set_status(
        client, customer_auth, customer["id"], False
    )
    anonymous_attempt = client.patch(
        f"/admin/customers/{customer['id']}/status",
        json={"is_active": False},
    )
    admin_target = _set_status(
        client, admin_auth, admin_auth["user"]["id"], False
    )
    missing = _set_status(
        client, admin_auth, 999999, False
    )
    invalid_body = client.patch(
        f"/admin/customers/{customer['id']}/status",
        headers=admin_auth["headers"],
        json={"is_active": "not-a-boolean"},
    )

    assert customer_attempt.status_code == 403
    assert anonymous_attempt.status_code == 401
    assert admin_target.status_code == 404
    assert missing.status_code == 404
    assert invalid_body.status_code == 422

    # The failed attempts left the customer active.
    login = _login(client, customer["email"])
    assert login.status_code == 200
