import itertools
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Configure an isolated database and upload folder before the app imports.
TEST_ROOT = Path(tempfile.mkdtemp(prefix="furzy-tests-"))
(TEST_ROOT / "uploads").mkdir(parents=True, exist_ok=True)

os.environ["DATABASE_URL"] = f"sqlite:///{(TEST_ROOT / 'test.db').as_posix()}"
os.environ["UPLOADS_DIR"] = str(TEST_ROOT / "uploads")
os.environ["JWT_SECRET"] = "test-only-jwt-secret-" + "x" * 40
os.environ["FRONTEND_ORIGINS"] = "http://127.0.0.1:5173"
os.environ["SHIPPING_FEE_LKR"] = "350"
os.environ["MAX_UPLOAD_BYTES"] = str(5 * 1024 * 1024)

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.rate_limit import (  # noqa: E402
    login_account_limiter,
    login_ip_limiter,
)
from app.security import hash_password  # noqa: E402

ADMIN_EMAIL = "admin@furzy.dev"
ADMIN_PASSWORD = "AdminPass123!"
CUSTOMER_EMAIL = "customer@furzy.dev"
CUSTOMER_PASSWORD = "CustomerPass123!"


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    login_account_limiter.clear()
    login_ip_limiter.clear()

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def admin_auth(client):
    with SessionLocal() as db:
        db.add(
            User(
                name="Test Admin",
                email=ADMIN_EMAIL,
                password_hash=hash_password(ADMIN_PASSWORD),
                role="admin",
            )
        )
        db.commit()

    response = client.post(
        "/auth/login",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text
    data = response.json()

    return {
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "user": data["user"],
    }


@pytest.fixture()
def customer_auth(client):
    response = client.post(
        "/auth/register",
        json={
            "name": "Test Customer",
            "email": CUSTOMER_EMAIL,
            "password": CUSTOMER_PASSWORD,
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()

    return {
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "user": data["user"],
    }


@pytest.fixture()
def create_product(client, admin_auth):
    counter = itertools.count(1)

    def _create_product(**overrides):
        index = next(counter)
        sku_prefix = overrides.pop("sku_prefix", f"TEST-{index}")
        name = overrides.pop("name", f"Test Tee {index}")
        price = overrides.pop("price", 2500)
        variants = overrides.pop(
            "variants",
            [
                {
                    "size": "M",
                    "color": "Black",
                    "sku": f"{sku_prefix}-M",
                    "stock": 8,
                },
                {
                    "size": "L",
                    "color": "Black",
                    "sku": f"{sku_prefix}-L",
                    "stock": 2,
                },
            ],
        )
        payload = {
            "name": name,
            "description": "Test product",
            "price": price,
            "images": ["/images/test.jpg"],
            "variants": variants,
            **overrides,
        }
        response = client.post(
            "/admin/products",
            headers=admin_auth["headers"],
            json=payload,
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _create_product


@pytest.fixture()
def product(create_product):
    return create_product()


@pytest.fixture()
def order_payload():
    return {
        "contact_name": "Test Customer",
        "phone": "0771234567",
        "address_line1": "123 Test Street",
        "city": "Colombo",
        "postal_code": "00100",
        "country": "Sri Lanka",
        "notes": "Test order",
        "payment_method": "cod",
    }
