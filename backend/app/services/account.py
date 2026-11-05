from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import security
from app.config import settings
from app.models import User
from app.models.common import utcnow
from app.services import auth_tokens


def issue_email_verification(
    db: Session, user: User
) -> str | None:
    if user.email_verified_at is not None:
        return None

    return auth_tokens.issue_token(
        db,
        user,
        auth_tokens.EMAIL_VERIFICATION,
        timedelta(hours=settings.email_verification_token_hours),
    )


def verify_email(db: Session, raw_token: str) -> User:
    token = auth_tokens.consume_token(
        db, raw_token, auth_tokens.EMAIL_VERIFICATION
    )

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "This verification link is invalid or has expired."
            ),
        )

    user = db.get(User, token.user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "This verification link is invalid or has expired."
            ),
        )

    user.email_verified_at = utcnow()
    db.commit()
    db.refresh(user)

    return user


def request_password_reset(
    db: Session, email: str
) -> tuple[User | None, str | None]:
    normalized = email.strip().lower()
    user = db.scalar(
        select(User).where(
            User.email == normalized,
            User.is_active.is_(True),
        )
    )

    if user is None:
        return None, None

    raw_token = auth_tokens.issue_token(
        db,
        user,
        auth_tokens.PASSWORD_RESET,
        timedelta(minutes=settings.password_reset_token_minutes),
    )

    return user, raw_token


def reset_password(
    db: Session, raw_token: str, new_password: str
) -> User:
    token = auth_tokens.consume_token(
        db, raw_token, auth_tokens.PASSWORD_RESET
    )

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "This password reset link is invalid or has expired."
            ),
        )

    user = db.get(User, token.user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "This password reset link is invalid or has expired."
            ),
        )

    user.password_hash = security.hash_password(new_password)
    # Invalidate every access and refresh token issued before now.
    user.token_version = int(user.token_version or 0) + 1

    db.commit()
    db.refresh(user)

    return user


def find_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(
        select(User).where(
            User.email == email.strip().lower(),
            User.is_active.is_(True),
        )
    )
