"""Fail-fast production configuration check.

Run this with the production environment variables loaded before deploying:

    APP_ENV=production python -m app.check_production

It never prints secret values.
"""

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text

from app.config import Settings, settings


@dataclass
class Check:
    status: str
    name: str
    detail: str = ""


def _result(ok: bool, name: str, detail: str = "") -> Check:
    return Check("PASS" if ok else "FAIL", name, detail)


def environment_checks(config: Settings) -> list[Check]:
    checks: list[Check] = []

    checks.append(
        _result(
            config.is_production,
            "APP_ENV",
            (
                "production"
                if config.is_production
                else "must be production for this check"
            ),
        )
    )

    database_url = config.database_url.strip().lower()
    checks.append(
        _result(
            database_url.startswith("postgresql+psycopg://"),
            "DATABASE_URL",
            (
                "PostgreSQL with psycopg is required"
                if not database_url.startswith(
                    "postgresql+psycopg://"
                )
                else "PostgreSQL"
            ),
        )
    )

    if database_url.startswith("postgresql+psycopg://"):
        checks.append(
            Check(
                "PASS" if "sslmode=" in database_url else "WARN",
                "DATABASE_SSL",
                (
                    "sslmode is configured"
                    if "sslmode=" in database_url
                    else "add sslmode=require when the provider supports it"
                ),
            )
        )

    migration_url = config.alembic_database_url.strip()
    migration_url_lower = migration_url.lower()

    if config.migration_database_url.strip():
        checks.append(
            _result(
                migration_url_lower.startswith(
                    "postgresql+psycopg://"
                ),
                "MIGRATION_DATABASE_URL",
                (
                    "direct migration URL configured"
                    if migration_url_lower.startswith(
                        "postgresql+psycopg://"
                    )
                    else "must use postgresql+psycopg://"
                ),
            )
        )

        if migration_url_lower.startswith(
            "postgresql+psycopg://"
        ):
            checks.append(
                Check(
                    "PASS"
                    if "sslmode=" in migration_url_lower
                    else "WARN",
                    "MIGRATION_DATABASE_SSL",
                    (
                        "sslmode is configured"
                        if "sslmode=" in migration_url_lower
                        else "add sslmode=require when the provider "
                        "supports it"
                    ),
                )
            )
            checks.append(
                Check(
                    "WARN"
                    if "-pooler" in migration_url_lower
                    else "PASS",
                    "MIGRATION_DATABASE_POOLING",
                    (
                        "migration URL uses a pooled endpoint; use the "
                        "direct Neon URL for Alembic"
                        if "-pooler" in migration_url_lower
                        else "migration URL is not pooled"
                    ),
                )
            )
    elif "-pooler" in database_url:
        checks.append(
            Check(
                "WARN",
                "MIGRATION_DATABASE_URL",
                "DATABASE_URL uses a pooled Neon endpoint; set the "
                "direct connect URL here so Alembic migrations do not "
                "run through PgBouncer",
            )
        )
    else:
        checks.append(
            Check(
                "PASS",
                "MIGRATION_DATABASE_URL",
                "not set; Alembic falls back to DATABASE_URL",
            )
        )

    checks.append(
        _result(
            len(config.jwt_secret) >= 32
            and config.jwt_secret != "dev-secret-change-me",
            "JWT_SECRET",
            (
                "strong secret configured"
                if len(config.jwt_secret) >= 32
                else "must be at least 32 characters and non-default"
            ),
        )
    )

    origins = config.cors_origins
    invalid_origins = [
        origin
        for origin in origins
        if (
            "*" in origin
            or origin.startswith("http://")
            or "localhost" in origin
            or "127.0.0.1" in origin
        )
    ]
    checks.append(
        _result(
            bool(origins) and not invalid_origins,
            "FRONTEND_ORIGINS",
            (
                "final frontend origin(s) configured"
                if origins and not invalid_origins
                else "must list the exact HTTPS production "
                "frontend origin(s), with no wildcard or localhost"
            ),
        )
    )

    for name, value in (
        ("BACKEND_PUBLIC_URL", config.backend_public_url),
        ("FRONTEND_BASE_URL", config.frontend_base_url),
    ):
        checks.append(
            _result(
                value.strip().lower().startswith("https://"),
                name,
                "must be a public HTTPS URL",
            )
        )

    provider = config.normalized_payment_provider
    checks.append(
        _result(
            provider == "payhere",
            "PAYMENT_PROVIDER",
            (
                "payhere"
                if provider == "payhere"
                else "must be payhere in production"
            ),
        )
    )
    checks.append(
        _result(
            not config.payment_mock_enabled,
            "PAYMENT_MOCK_ENABLED",
            "must be false in production",
        )
    )
    checks.append(
        _result(
            bool(config.payhere_merchant_id.strip())
            and bool(config.payhere_merchant_secret.strip()),
            "PAYHERE_CHECKOUT_CREDENTIALS",
            "merchant ID and secret are required",
        )
    )
    checks.append(
        Check(
            "WARN" if config.payhere_sandbox else "PASS",
            "PAYHERE_SANDBOX",
            (
                "sandbox is still enabled; switch to live after "
                "verification"
                if config.payhere_sandbox
                else "live mode"
            ),
        )
    )
    checks.append(
        Check(
            "PASS" if config.payhere_api_enabled else "WARN",
            "PAYHERE_API_CREDENTIALS",
            (
                "Merchant API enabled"
                if config.payhere_api_enabled
                else "automatic retrieval/refunds disabled; manual "
                "reconciliation will be used"
            ),
        )
    )

    checks.append(
        _result(
            config.smtp_configured,
            "SMTP",
            (
                "configured"
                if config.smtp_configured
                else "SMTP_HOST and SMTP_FROM_EMAIL are required for "
                "verification, reset, and notification emails"
            ),
        )
    )

    if config.email_verification_required:
        checks.append(
            _result(
                config.smtp_configured,
                "EMAIL_VERIFICATION_REQUIRED",
                (
                    "verification is enabled and email delivery is "
                    "configured"
                    if config.smtp_configured
                    else "verification is required but SMTP is not "
                    "configured"
                ),
            )
        )

    checks.append(
        _result(
            bool(config.admin_email.strip()),
            "ADMIN_EMAIL",
            "needed to seed the first admin account",
        )
    )

    uploads = Path(config.uploads_dir)
    writable = False

    try:
        uploads.mkdir(parents=True, exist_ok=True)
        probe = uploads / ".write-check"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        writable = True
    except OSError:
        writable = False

    checks.append(
        _result(
            writable,
            "UPLOADS_DIR",
            (
                f"{uploads} (local fallback/cache)"
                if writable
                else "local fallback directory must be writable"
            ),
        )
    )
    checks.append(
        Check(
            "PASS",
            "UPLOAD_STORAGE",
            "uploaded product images are stored in PostgreSQL; "
            "UPLOADS_DIR is only a local fallback/cache",
        )
    )

    return checks


def database_check() -> Check:
    from app.database import engine

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        return Check(
            "FAIL",
            "database connection",
            type(exc).__name__,
        )

    return Check("PASS", "database connection", "SELECT 1 succeeded")


FREE_DEMO_OPTIONAL_CHECKS = {
    "PAYHERE_CHECKOUT_CREDENTIALS",
    "SMTP",
    "ADMIN_EMAIL",
}


def _apply_free_demo_mode(
    checks: list[Check], config: Settings
) -> None:
    for check in checks:
        if (
            check.name in FREE_DEMO_OPTIONAL_CHECKS
            and check.status == "FAIL"
        ):
            check.status = "WARN"
            check.detail = (
                f"{check.detail} (optional for the free demo)"
                if check.detail
                else "optional for the free demo"
            )

    for check in checks:
        if check.name == "PAYHERE_SANDBOX":
            if config.payhere_sandbox:
                check.status = "PASS"
                check.detail = (
                    "sandbox mode is required for the free demo"
                )
            else:
                check.status = "FAIL"
                check.detail = (
                    "live PayHere mode is not allowed for the free demo"
                )
        elif (
            check.name == "MIGRATION_DATABASE_URL"
            and check.status == "WARN"
        ):
            check.status = "PASS"
            check.detail = (
                "not needed on Render Free; use the Neon direct URL "
                "locally for Alembic"
            )


def run_checks(
    config: Settings, *, free_demo: bool = False
) -> int:
    checks = environment_checks(config)

    if free_demo:
        _apply_free_demo_mode(checks, config)

    checks.append(database_check())
    failures = 0
    warnings = 0

    for check in checks:
        suffix = f" - {check.detail}" if check.detail else ""
        print(f"[{check.status}] {check.name}{suffix}")

        if check.status == "FAIL":
            failures += 1
        elif check.status == "WARN":
            warnings += 1

    print(
        f"\n{failures} failure(s), {warnings} warning(s)."
    )
    return 0 if failures == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate production settings before deploying FURZY."
        )
    )
    parser.add_argument(
        "--free-demo",
        action="store_true",
        help=(
            "Treat missing SMTP, admin-email, and PayHere checkout "
            "credentials as warnings for the free demo deployment."
        ),
    )
    args = parser.parse_args(argv)

    if os.environ.get("APP_ENV", "").strip().lower() not in {
        "production",
        "prod",
    }:
        print(
            "Set APP_ENV=production with the production environment "
            "loaded before running this check."
        )

    return run_checks(
        settings, free_demo=args.free_demo
    )


if __name__ == "__main__":
    sys.exit(main())
