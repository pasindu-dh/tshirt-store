import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import (
    settings,
    validate_payment_security,
    validate_runtime_security,
)
from app.database import SessionLocal
from app.routers import (
    admin,
    admin_coupons,
    admin_customers,
    admin_exports,
    admin_inventory,
    admin_notifications,
    admin_orders,
    admin_refunds,
    admin_reports,
    admin_returns,
    admin_stats,
    auth,
    cart,
    categories,
    coupons,
    health,
    orders,
    payments,
    products,
    return_policy,
    returns,
    reviews,
    uploads,
    wishlist,
)
from app.services.stock import expire_unpaid_online_orders

logger = logging.getLogger("furzy")

BASE_DIR = Path(__file__).resolve().parent.parent
IMAGES_DIR = BASE_DIR / "images"
UPLOADS_DIR = Path(settings.uploads_dir)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

validate_payment_security(settings)
validate_runtime_security(settings)

if (
    len(settings.jwt_secret) < 32
    or settings.jwt_secret == "dev-secret-change-me"
):
    logger.warning(
        "JWT_SECRET is weak or still the development default. "
        "Set a strong secret in backend/.env before deploying."
    )

if settings.normalized_payment_provider == "mock":
    if settings.payment_mock_enabled:
        logger.warning(
            "Mock online payments are enabled. Never use this mode "
            "in production."
        )
elif settings.normalized_payment_provider == "payhere":
    if not settings.online_payments_enabled:
        logger.warning(
            "PAYMENT_PROVIDER=payhere but PayHere credentials are "
            "incomplete; online payments are disabled."
        )
elif settings.normalized_payment_provider not in {
    "disabled",
    "payhere",
    "mock",
}:
    logger.warning(
        "Unknown PAYMENT_PROVIDER value; online payments are disabled."
    )


def _expire_reservations_once() -> None:
    with SessionLocal() as db:
        expired = expire_unpaid_online_orders(db)

        if expired:
            logger.info(
                "Expired %s unpaid online order reservation(s).",
                expired,
            )


async def _reservation_sweeper() -> None:
    interval = max(10, settings.stock_reservation_sweep_seconds)

    while True:
        await asyncio.sleep(interval)

        try:
            await asyncio.to_thread(_expire_reservations_once)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Stock reservation sweep failed.")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = None

    if settings.stock_reservation_sweep_enabled:
        task = asyncio.create_task(_reservation_sweeper())

    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Catalog, authentication, cart, order, and payment API for "
        "the FURZY T-shirt store. Admin routes require a bearer token "
        "with the admin role."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault(
        "Referrer-Policy", "strict-origin-when-cross-origin"
    )
    response.headers.setdefault(
        "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
    )

    if (
        request.url.scheme == "https"
        or request.headers.get("x-forwarded-proto") == "https"
    ):
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )

    return response


# Serve images from an absolute path so the server works from any directory.
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

app.include_router(products.router)
app.include_router(categories.router)
app.include_router(auth.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(returns.router)
app.include_router(return_policy.router)
app.include_router(payments.router)
app.include_router(reviews.router)
app.include_router(wishlist.router)
app.include_router(coupons.router)
app.include_router(admin.router)
app.include_router(admin_coupons.router)
app.include_router(admin_orders.router)
app.include_router(admin_returns.router)
app.include_router(admin_reports.router)
app.include_router(admin_inventory.router)
app.include_router(admin_customers.router)
app.include_router(admin_notifications.router)
app.include_router(admin_refunds.router)
app.include_router(admin_exports.router)
app.include_router(health.router)
app.include_router(admin_stats.router)
app.include_router(uploads.router)


@app.get("/", tags=["health"])
def home():
    return {"message": "Backend working"}
