from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "FURZY T-Shirt Store API"
    app_version: str = "0.5.0"

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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
