from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import admin, categories, products

BASE_DIR = Path(__file__).resolve().parent.parent
IMAGES_DIR = BASE_DIR / "images"

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Catalog API for the FURZY T-shirt store. "
        "Admin routes are unprotected until Phase 2 authentication is added."
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

# Serve images from an absolute path so the server works from any directory.
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")

app.include_router(products.router)
app.include_router(categories.router)
app.include_router(admin.router)


@app.get("/", tags=["health"])
def home():
    return {"message": "Backend working"}
