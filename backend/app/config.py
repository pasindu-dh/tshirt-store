from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "FURZY T-Shirt Store API"
    app_version: str = "0.9.4"
    app_env: str = "development"

    # Default to an absolute path so the database location never depends on CWD.
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'store.db').as_posix()}"

    # Uploaded product images.
    uploads_dir: str = str(BACKEND_DIR / "uploads")
    max_upload_bytes: int = 5 * 1024 * 1024

    # Store checkout settings.
    shipping_fee_lkr: int = 350

    frontend_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Authentication. Set a strong JWT_SECRET before deploying.
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # SMTP order notifications. Leave SMTP_HOST empty to disable sending.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_tls: bool = True

    # Online payments. PAYMENT_PROVIDER can be "disabled", "mock", or
    # "payhere". Mock mode is for tests/local development only.
    payment_provider: str = "disabled"
    payment_currency: str = "LKR"
    payment_mock_enabled: bool = False
    payhere_merchant_id: str = ""
    payhere_merchant_secret: str = ""
    payhere_sandbox: bool = True
    payhere_api_app_id: str = ""
    payhere_api_app_secret: str = ""
    payhere_api_timeout_seconds: int = 10
    frontend_base_url: str = "http://127.0.0.1:5173"
    backend_public_url: str = "http://127.0.0.1:8005"

    # Unpaid online orders release their reserved stock after this period.
    online_payment_reservation_minutes: int = 30
    stock_reservation_sweep_enabled: bool = True
    stock_reservation_sweep_seconds: int = 60

    # Admin account managed by `python -m app.seed_admin`.
    # There are intentionally no default email/password values. Set
    # ADMIN_EMAIL and ADMIN_PASSWORD in backend/.env; seed_admin refuses
    # to run with missing, invalid, or known default/placeholder values.
    admin_name: str = "Store Admin"
    admin_email: str = ""
    admin_password: str = ""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.frontend_origins.split(",")
            if origin.strip()
        ]

    @property
    def normalized_payment_provider(self) -> str:
        return self.payment_provider.strip().lower()

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() in {"production", "prod"}

    @property
    def online_payments_enabled(self) -> bool:
        provider = self.normalized_payment_provider

        if provider == "payhere":
            return bool(
                self.payhere_merchant_id.strip()
                and self.payhere_merchant_secret.strip()
            )

        if provider == "mock":
            return self.payment_mock_enabled and not self.is_production

        return False

    @property
    def payhere_api_enabled(self) -> bool:
        provider = self.normalized_payment_provider

        if provider == "mock":
            return self.payment_mock_enabled and not self.is_production

        if provider == "payhere":
            return bool(
                self.payhere_api_app_id.strip()
                and self.payhere_api_app_secret.strip()
            )

        return False


def validate_payment_security(settings: Settings) -> None:
    """Fail startup rather than expose mock payment completion in production."""

    if settings.is_production and (
        settings.payment_mock_enabled
        or settings.normalized_payment_provider == "mock"
    ):
        raise RuntimeError(
            "Mock online payments cannot be enabled when APP_ENV=production."
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
