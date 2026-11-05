from app.check_production import environment_checks
from app.config import Settings
from app.payhere_check import config_checks


def _production_settings(tmp_path, **overrides):
    values = {
        "app_env": "production",
        "database_url": (
            "postgresql+psycopg://user:pass@db.example.com:5432/"
            "furzy?sslmode=require"
        ),
        "uploads_dir": str(tmp_path / "uploads"),
        "jwt_secret": "p" * 64,
        "frontend_origins": "https://shop.example.com",
        "backend_public_url": "https://api.example.com",
        "frontend_base_url": "https://shop.example.com",
        "payment_provider": "payhere",
        "payhere_merchant_id": "merchant",
        "payhere_merchant_secret": "secret",
        "payhere_sandbox": False,
        "payhere_api_app_id": "app-id",
        "payhere_api_app_secret": "app-secret",
        "payment_mock_enabled": False,
        "smtp_host": "smtp.example.com",
        "smtp_from_email": "orders@example.com",
        "email_verification_required": True,
        "admin_email": "admin@example.com",
    }
    values.update(overrides)
    return Settings(**values)


def test_well_configured_production_environment_passes(tmp_path):
    config = _production_settings(tmp_path)
    checks = environment_checks(config)
    failures = [
        check for check in checks if check.status == "FAIL"
    ]

    assert failures == [], [
        (check.name, check.detail) for check in failures
    ]
    names = {check.name for check in checks}
    assert {
        "APP_ENV",
        "DATABASE_URL",
        "JWT_SECRET",
        "FRONTEND_ORIGINS",
        "PAYMENT_PROVIDER",
        "PAYHERE_CHECKOUT_CREDENTIALS",
        "SMTP",
        "UPLOADS_DIR",
    } <= names


def test_unsafe_defaults_are_reported(tmp_path):
    config = _production_settings(
        tmp_path,
        app_env="development",
        database_url="sqlite:///store.db",
        jwt_secret="dev-secret-change-me",
        frontend_origins="*",
        backend_public_url="http://127.0.0.1:8005",
        frontend_base_url="http://127.0.0.1:5173",
        payment_provider="mock",
        payment_mock_enabled=True,
        payhere_merchant_id="",
        payhere_merchant_secret="",
        smtp_host="",
        smtp_from_email="",
        email_verification_required=True,
    )
    checks = environment_checks(config)
    failed = {
        check.name
        for check in checks
        if check.status == "FAIL"
    }

    assert {
        "APP_ENV",
        "DATABASE_URL",
        "JWT_SECRET",
        "FRONTEND_ORIGINS",
        "BACKEND_PUBLIC_URL",
        "FRONTEND_BASE_URL",
        "PAYMENT_PROVIDER",
        "PAYMENT_MOCK_ENABLED",
        "PAYHERE_CHECKOUT_CREDENTIALS",
        "SMTP",
        "EMAIL_VERIFICATION_REQUIRED",
    } <= failed


def test_payhere_sandbox_configuration_checks(tmp_path):
    good = _production_settings(
        tmp_path,
        payhere_sandbox=True,
        backend_public_url="https://api.example.com",
    )
    results = config_checks(good)
    assert [
        check for check in results if check.status == "FAIL"
    ] == []
    notify = next(
        check
        for check in results
        if check.name == "NOTIFY_URL"
    )
    assert "https://api.example.com/payments/payhere/notify" in (
        notify.detail
    )

    bad = _production_settings(
        tmp_path,
        payment_provider="disabled",
        payhere_merchant_id="",
        payhere_merchant_secret="",
        payhere_api_app_id="",
        payhere_api_app_secret="",
        payment_mock_enabled=True,
        backend_public_url="http://127.0.0.1:8005",
    )
    failed = {
        check.name
        for check in config_checks(bad)
        if check.status == "FAIL"
    }
    assert {
        "PAYMENT_PROVIDER",
        "PAYHERE_CHECKOUT_CREDENTIALS",
        "PAYMENT_MOCK_ENABLED",
    } <= failed
