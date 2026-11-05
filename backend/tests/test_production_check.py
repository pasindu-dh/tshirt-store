from app.check_production import (
    Check,
    _apply_free_demo_mode,
    environment_checks,
)
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


def test_origin_trailing_slash_is_normalized(tmp_path):
    config = _production_settings(
        tmp_path,
        frontend_origins="https://shop.example.com/",
    )
    assert config.cors_origins == ["https://shop.example.com"]
    checks = environment_checks(config)
    origins = next(
        check
        for check in checks
        if check.name == "FRONTEND_ORIGINS"
    )
    assert origins.status == "PASS"


def test_pooled_neon_url_requires_a_direct_migration_url(
    tmp_path,
):
    pooled = (
        "postgresql+psycopg://user:pass@"
        "ep-cool-name-pooler.us-east-2.aws.neon.tech/"
        "furzy?sslmode=require"
    )
    config = _production_settings(
        tmp_path, database_url=pooled
    )
    checks = environment_checks(config)
    migration = next(
        check
        for check in checks
        if check.name == "MIGRATION_DATABASE_URL"
    )
    assert migration.status == "WARN"
    assert "pooled" in migration.detail

    direct = (
        "postgresql+psycopg://user:pass@"
        "ep-cool-name.us-east-2.aws.neon.tech/"
        "furzy?sslmode=require"
    )
    configured = _production_settings(
        tmp_path,
        database_url=pooled,
        migration_database_url=direct,
    )
    checks = environment_checks(configured)
    migration = next(
        check
        for check in checks
        if check.name == "MIGRATION_DATABASE_URL"
    )
    ssl_check = next(
        check
        for check in checks
        if check.name == "MIGRATION_DATABASE_SSL"
    )
    assert migration.status == "PASS"
    assert ssl_check.status == "PASS"
    pooling = next(
        check
        for check in checks
        if check.name == "MIGRATION_DATABASE_POOLING"
    )
    assert pooling.status == "PASS"


def test_free_demo_downgrades_only_optional_failures(
    tmp_path,
):
    config = _production_settings(
        tmp_path, payhere_sandbox=True
    )
    checks = [
        Check("FAIL", "SMTP", "missing"),
        Check(
            "FAIL",
            "PAYHERE_CHECKOUT_CREDENTIALS",
            "missing",
        ),
        Check("FAIL", "DATABASE_URL", "not postgres"),
        Check("WARN", "PAYHERE_SANDBOX", "sandbox"),
        Check("WARN", "MIGRATION_DATABASE_URL", "pooled"),
    ]
    _apply_free_demo_mode(checks, config)

    assert checks[0].status == "WARN"
    assert "optional" in checks[0].detail
    assert checks[1].status == "WARN"
    assert checks[2].status == "FAIL"
    assert checks[3].status == "PASS"
    assert "required" in checks[3].detail
    assert checks[4].status == "PASS"

    live_config = _production_settings(
        tmp_path, payhere_sandbox=False
    )
    live_checks = [
        Check("WARN", "PAYHERE_SANDBOX", "live")
    ]
    _apply_free_demo_mode(live_checks, live_config)
    assert live_checks[0].status == "FAIL"
    assert "not allowed" in live_checks[0].detail


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
