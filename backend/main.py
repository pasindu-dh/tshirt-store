import os
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
IMAGES_DIR = BASE_DIR / "images"

app = FastAPI(title="FURZY T-Shirt Store API", version="0.1.0")

# Comma-separated list of frontend origins allowed to call the API.
frontend_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve images from an absolute path so the server works from any directory.
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")

# Temporary in-memory catalog until the database is added in Phase 1.
image_files = sorted(path.name for path in IMAGES_DIR.glob("t_shirt_*.jpg"))

all_products = [
    {
        "id": product_id,
        "name": f"Product {product_id}",
        "price": 1000 + product_id * 500,
        "image": f"/images/{image_files[(product_id - 1) % len(image_files)]}",
    }
    for product_id in range(1, 31)
]


@app.get("/")
def home():
    return {"message": "Backend working"}


@app.get("/products")
def get_products(
    page: int = Query(1, ge=1),
    limit: int = Query(6, ge=1, le=100),
):
    start = (page - 1) * limit
    return all_products[start : start + limit]
