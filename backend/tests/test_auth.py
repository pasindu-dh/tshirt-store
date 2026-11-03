def test_register_login_me_and_refresh(client):
    register = client.post(
        "/auth/register",
        json={
            "name": "Round Trip",
            "email": "roundtrip@furzy.dev",
            "password": "RoundTripPass123!",
        },
    )
    assert register.status_code == 201, register.text
    registered = register.json()
    assert registered["user"]["role"] == "customer"
    assert "password" not in registered["user"]
    assert "password_hash" not in registered["user"]

    login = client.post(
        "/auth/login",
        data={
            "username": "roundtrip@furzy.dev",
            "password": "RoundTripPass123!",
        },
    )
    assert login.status_code == 200, login.text
    tokens = login.json()

    me = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "roundtrip@furzy.dev"

    refreshed = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]

    refresh_as_access = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
    )
    assert refresh_as_access.status_code == 401

    wrong_password = client.post(
        "/auth/login",
        data={
            "username": "roundtrip@furzy.dev",
            "password": "WrongPassword123!",
        },
    )
    assert wrong_password.status_code == 401


def test_duplicate_registration_is_rejected(client):
    payload = {
        "name": "Duplicate",
        "email": "duplicate@furzy.dev",
        "password": "DuplicatePass123!",
    }
    first = client.post("/auth/register", json=payload)
    duplicate = client.post("/auth/register", json=payload)

    assert first.status_code == 201
    assert duplicate.status_code == 409


def test_short_password_is_rejected(client):
    response = client.post(
        "/auth/register",
        json={
            "name": "Short",
            "email": "short@furzy.dev",
            "password": "short",
        },
    )
    assert response.status_code == 422


def test_admin_routes_require_admin_role(
    client, admin_auth, customer_auth
):
    anonymous = client.get("/admin/products")
    customer = client.get(
        "/admin/products", headers=customer_auth["headers"]
    )
    admin = client.get("/admin/products", headers=admin_auth["headers"])

    assert anonymous.status_code == 401
    assert customer.status_code == 403
    assert admin.status_code == 200


def test_login_rate_limit_blocks_repeated_failures(client):
    payload = {
        "username": "bruteforce@furzy.dev",
        "password": "WrongPassword123!",
    }

    for _ in range(5):
        response = client.post("/auth/login", data=payload)
        assert response.status_code == 401

    blocked = client.post("/auth/login", data=payload)
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1
    assert "Too many login attempts" in blocked.json()["detail"]


def test_security_headers_and_cors(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert (
        response.headers["Referrer-Policy"]
        == "strict-origin-when-cross-origin"
    )
    assert "Strict-Transport-Security" not in response.headers

    forwarded = client.get(
        "/", headers={"X-Forwarded-Proto": "https"}
    )
    assert (
        forwarded.headers["Strict-Transport-Security"]
        == "max-age=31536000; includeSubDomains"
    )

    preflight = client.options(
        "/products",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert preflight.status_code == 200
    assert (
        preflight.headers["access-control-allow-origin"]
        == "http://127.0.0.1:5173"
    )
