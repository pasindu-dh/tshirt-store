from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import jwt
from pwdlib import PasswordHash

from app.config import settings

if TYPE_CHECKING:
    from app.models import User

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return password_hasher.verify(plain_password, hashed_password)
    except Exception:
        return False


def _create_token(
    user: "User | int",
    token_type: str,
    expires_delta: timedelta,
) -> str:
    user_id = user if isinstance(user, int) else user.id
    token_version = (
        0 if isinstance(user, int) else int(user.token_version or 0)
    )
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "ver": token_version,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def create_access_token(user: "User | int") -> str:
    return _create_token(
        user,
        "access",
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user: "User | int") -> str:
    return _create_token(
        user,
        "refresh",
        timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token_claims(
    token: str, expected_type: str
) -> dict | None:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError:
        return None

    if payload.get("type") != expected_type:
        return None

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return None

    if user_id < 1:
        return None

    payload["user_id"] = user_id
    return payload


def token_matches_user(payload: dict, user: "User") -> bool:
    """Reject tokens issued before the user's last password reset."""

    if payload.get("user_id") != user.id:
        return False

    return int(payload.get("ver") or 0) == int(
        user.token_version or 0
    )


def decode_token(token: str, expected_type: str) -> int | None:
    payload = decode_token_claims(token, expected_type)

    if payload is None:
        return None

    return payload["user_id"]
