import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuthToken, User
from app.models.common import utcnow

EMAIL_VERIFICATION = "email_verification"
PASSWORD_RESET = "password_reset"


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def issue_token(
    db: Session,
    user: User,
    purpose: str,
    ttl: timedelta,
) -> str:
    """Create a single-use token and invalidate older ones for the purpose."""

    now = utcnow()
    previous = db.scalars(
        select(AuthToken).where(
            AuthToken.user_id == user.id,
            AuthToken.purpose == purpose,
            AuthToken.used_at.is_(None),
        )
    ).all()

    for token in previous:
        token.used_at = now

    raw_token = secrets.token_urlsafe(32)
    db.add(
        AuthToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=_hash_token(raw_token),
            expires_at=now + ttl,
        )
    )
    db.commit()

    return raw_token


def consume_token(
    db: Session,
    raw_token: str,
    purpose: str,
) -> AuthToken | None:
    """Consume a valid single-use token, or return None.

    The caller must commit the session after applying its changes.
    """

    if not raw_token or not raw_token.strip():
        return None

    token = db.scalar(
        select(AuthToken)
        .where(
            AuthToken.token_hash == _hash_token(raw_token.strip()),
            AuthToken.purpose == purpose,
        )
        .with_for_update()
    )

    if token is None or token.used_at is not None:
        return None

    if _as_utc(token.expires_at) <= utcnow():
        return None

    token.used_at = utcnow()
    return token
