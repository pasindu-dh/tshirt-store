import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import (
    admin,
    admin_orders,
    admin_stats,
    auth,
    cart,
    categories,
    orders,
    products,
    uploads,
)

logger = logging.getLogger("furzy")

BASE_DIR = Path(__file__).resolve().parent.parent
IMAGES_DIR = BASE_DIR / "images"
UPLOADS_DIR = Path(settings.uploads_dir)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

if (
    len(settings.jwt_secret) < 32
    or settings.jwt_secret == "dev-secret-change-me"
):
    logger.warning(
        "JWT_SECRET is weak or still the development default. "
        "Set a strong secret in backend/.env before deploying."
    )

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Catalog, authentication, cart, and order API for the FURZY "
        "T-shirt store. Admin routes require a bearer token with the "
        "admin role."
    ),
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
app.include_router(admin.router)
app.include_router(admin_orders.router)
app.include_router(admin_stats.router)
app.include_router(uploads.router)


@app.get("/", tags=["health"])
def home():
    return {"message": "Backend working"}
