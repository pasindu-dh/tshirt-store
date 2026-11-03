from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.database import SessionLocal
from app.models import User
from app.security import hash_password


def seed_admin() -> None:
    email = settings.admin_email.strip().lower()
    password = settings.admin_password

    if len(password) < 8:
        raise SystemExit("ADMIN_PASSWORD must be at least 8 characters.")

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))

        if user is None:
            user = User(
                name=settings.admin_name.strip() or "Store Admin",
                email=email,
                password_hash=hash_password(password),
                role="admin",
            )
            db.add(user)
            action = "Created"
        else:
            user.name = settings.admin_name.strip() or user.name
            user.role = "admin"
            user.password_hash = hash_password(password)
            action = "Updated"

        db.commit()

    print(f"{action} admin user: {email}")
    print(
        "Password: ADMIN_PASSWORD from backend/.env "
        "(default: ChangeMe123!)"
    )


def main() -> None:
    try:
        seed_admin()
    except OperationalError as exc:
        raise SystemExit(
            "Database tables were not found. Run `alembic upgrade head` first."
        ) from exc


if __name__ == "__main__":
    main()
