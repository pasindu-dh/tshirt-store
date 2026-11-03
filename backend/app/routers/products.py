from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.product import ProductOut
from app.services import catalog

SortOption = Literal["newest", "price_asc", "price_desc", "name"]

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
def list_products(
    response: Response,
    page: int = Query(1, ge=1),
    limit: int = Query(6, ge=1, le=100),
    search: str | None = Query(None, max_length=100),
    category: str | None = Query(None, max_length=140),
    sort: SortOption = Query("newest"),
    db: Session = Depends(get_db),
):
    products, total = catalog.list_products(
        db,
        page=page,
        limit=limit,
        search=search,
        category=category,
        sort=sort,
    )
    response.headers["X-Total-Count"] = str(total)
    return products


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = catalog.get_product(db, product_id, active_only=True)

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return product
