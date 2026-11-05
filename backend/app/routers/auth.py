from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import security
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.rate_limit import (
    login_account_limiter,
    login_ip_limiter,
    password_reset_account_limiter,
    password_reset_ip_limiter,
)
from app.schemas.auth import (
    AuthConfigOut,
    AuthResponse,
    EmailVerificationRequest,
    EmailVerificationResendRequest,
    MessageOut,
    PasswordForgotRequest,
    PasswordResetRequest,
    RefreshRequest,
    UserOut,
    UserRegister,
)
from app.services import account
from app.services.email import (
    send_email_verification,
    send_password_reset,
)

router = APIRouter(prefix="/auth", tags=["auth"])

RESET_REQUEST_MESSAGE = (
    "If an account exists for that email address, a password reset "
    "link has been sent."
)
VERIFICATION_SENT_MESSAGE = (
    "If that account needs verification, a new verification link has "
    "been sent."
)


def _auth_response(user: User) -> AuthResponse:
    return AuthResponse(
        access_token=security.create_access_token(user),
        refresh_token=security.create_refresh_token(user),
        user=UserOut.model_validate(user),
    )


def _verify_url(token: str) -> str:
    base = settings.frontend_base_url.rstrip("/")
    return f"{base}/verify-email?token={token}"


def _reset_url(token: str) -> str:
    base = settings.frontend_base_url.rstrip("/")
    return f"{base}/reset-password?token={token}"


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get("/config", response_model=AuthConfigOut)
def auth_config():
    return AuthConfigOut(
        email_verification_required=settings.email_verification_required,
        email_verification_available=settings.smtp_configured,
        password_reset_available=settings.smtp_configured,
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: UserRegister,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    email = str(payload.email).strip().lower()

    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    user = User(
        name=payload.name,
        email=email,
        password_hash=security.hash_password(payload.password),
        role="customer",
    )
    db.add(user)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from exc

    db.refresh(user)

    if settings.smtp_configured:
        token = account.issue_email_verification(db, user)

        if token:
            background_tasks.add_task(
                send_email_verification,
                user.email,
                user.name,
                _verify_url(token),
                settings.email_verification_token_hours,
            )

    return _auth_response(user)


@router.post("/login", response_model=AuthResponse)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    email = form_data.username.strip().lower()
    client_ip = _client_ip(request)
    account_key = f"account:{email}"
    ip_key = f"ip:{client_ip}"

    retry_after = max(
        login_account_limiter.retry_after(account_key),
        login_ip_limiter.retry_after(ip_key),
    )

    if retry_after > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    user = db.scalar(select(User).where(User.email == email))

    if user is None or not security.verify_password(
        form_data.password, user.password_hash
    ):
        login_account_limiter.record_failure(account_key)
        login_ip_limiter.record_failure(ip_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    login_account_limiter.reset(account_key)
    login_ip_limiter.reset(ip_key)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )

    if (
        settings.email_verification_required
        and not user.email_verified
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Please verify your email address before signing in. "
                "You can request a new verification link from the "
                "verification page."
            ),
        )

    return _auth_response(user)


@router.post("/refresh", response_model=AuthResponse)
def refresh_tokens(payload: RefreshRequest, db: Session = Depends(get_db)):
    claims = security.decode_token_claims(
        payload.refresh_token, "refresh"
    )

    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get(User, claims["user_id"])

    if (
        user is None
        or not user.is_active
        or not security.token_matches_user(claims, user)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if (
        settings.email_verification_required
        and not user.email_verified
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email verification required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _auth_response(user)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post(
    "/verify-email",
    response_model=MessageOut,
)
def verify_email(
    payload: EmailVerificationRequest,
    db: Session = Depends(get_db),
):
    account.verify_email(db, payload.token)
    return MessageOut(
        message="Your email address has been verified."
    )


@router.post(
    "/verify-email/resend",
    response_model=MessageOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def resend_verification(
    payload: EmailVerificationResendRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = account.find_user_by_email(db, str(payload.email))

    if user is not None and not user.email_verified:
        token = account.issue_email_verification(db, user)

        if token:
            background_tasks.add_task(
                send_email_verification,
                user.email,
                user.name,
                _verify_url(token),
                settings.email_verification_token_hours,
            )

    return MessageOut(message=VERIFICATION_SENT_MESSAGE)


@router.post(
    "/password/forgot",
    response_model=MessageOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def forgot_password(
    payload: PasswordForgotRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    email = str(payload.email).strip().lower()
    account_key = f"reset:{email}"
    ip_key = f"reset-ip:{_client_ip(request)}"
    retry_after = max(
        password_reset_account_limiter.retry_after(account_key),
        password_reset_ip_limiter.retry_after(ip_key),
    )

    if retry_after > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Too many password reset requests. Try again later."
            ),
            headers={"Retry-After": str(retry_after)},
        )

    password_reset_account_limiter.record_failure(account_key)
    password_reset_ip_limiter.record_failure(ip_key)

    user, token = account.request_password_reset(db, email)

    if user is not None and token is not None:
        background_tasks.add_task(
            send_password_reset,
            user.email,
            user.name,
            _reset_url(token),
            settings.password_reset_token_minutes,
        )

    return MessageOut(message=RESET_REQUEST_MESSAGE)


@router.post(
    "/password/reset",
    response_model=MessageOut,
)
def reset_password(
    payload: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = account.reset_password(
        db, payload.token, payload.new_password
    )
    password_reset_account_limiter.reset(f"reset:{user.email}")
    password_reset_ip_limiter.reset(
        f"reset-ip:{_client_ip(request)}"
    )

    return MessageOut(
        message=(
            "Your password has been reset. Sign in with your new "
            "password."
        )
    )
