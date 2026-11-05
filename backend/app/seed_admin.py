from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.database import SessionLocal
from app.models import User
from app.models.common import utcnow
from app.security import hash_password

MIN_ADMIN_PASSWORD_LENGTH = 8
BLOCKED_ADMIN_EMAILS = {
    "admin@furzy.local",
    "admin@example.com",
}
BLOCKED_ADMIN_PASSWORDS = {
    "changeme123!",
    "replace-with-a-strong-password",
    "password",
    "admin",
    "admin123",
}
email_adapter = TypeAdapter(EmailStr)


def validate_admin_config(email: str, password: str) -> str:
    normalized_email = (email or "").strip().lower()

    if not normalized_email:
        raise ValueError("ADMIN_EMAIL is required.")

    if normalized_email in BLOCKED_ADMIN_EMAILS:
        raise ValueError(
            "Refusing to use a known default or placeholder admin email."
        )

    try:
        normalized_email = (
            str(email_adapter.validate_python(normalized_email))
            .strip()
            .lower()
        )
    except ValidationError as exc:
        raise ValueError("ADMIN_EMAIL is not a valid email address.") from exc

    if not password:
        raise ValueError("ADMIN_PASSWORD is required.")

    if len(password) < MIN_ADMIN_PASSWORD_LENGTH:
        raise ValueError(
            "ADMIN_PASSWORD must be at least "
            f"{MIN_ADMIN_PASSWORD_LENGTH} characters."
        )

    if password.strip().casefold() in BLOCKED_ADMIN_PASSWORDS:
        raise ValueError(
            "Refusing to use a known default or placeholder admin password."
        )

    return normalized_email


def seed_admin() -> None:
    email = validate_admin_config(
        settings.admin_email, settings.admin_password
    )
    password = settings.admin_password
    name = settings.admin_name.strip() or "Store Admin"

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))

        if user is None:
            user = User(
                name=name,
                email=email,
                password_hash=hash_password(password),
                role="admin",
                # Admin accounts are provisioned by an operator, so they
                # are trusted without going through the customer email
                # verification flow.
                email_verified_at=utcnow(),
            )
            db.add(user)
            action = "Created"
        else:
            user.name = name
            user.role = "admin"
            user.password_hash = hash_password(password)
            user.email_verified_at = (
                user.email_verified_at or utcnow()
            )
            action = "Updated"

        db.commit()

    print(f"{action} configured admin account.")
    print("Password: the ADMIN_PASSWORD value from backend/.env")


def main() -> None:
    try:
        seed_admin()
    except ValueError as exc:
        raise SystemExit(f"Admin configuration error: {exc}") from exc
    except OperationalError as exc:
        raise SystemExit(
            "Database tables were not found. Run `alembic upgrade head` first."
        ) from exc


if __name__ == "__main__":
    main()
