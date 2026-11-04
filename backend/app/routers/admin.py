"""Admin catalog endpoints.

Every route in this module requires a bearer token belonging to a user with
the admin role (see `app.dependencies.require_admin`).
"""

from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import User
from app.schemas.catalog_import import CatalogImportResultOut
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate
from app.services import catalog, catalog_import

MAX_CATALOG_IMPORT_BYTES = 2 * 1024 * 1024

SortOption = Literal["newest", "price_asc", "price_desc", "name"]

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


def _require_product(product_id: int, db: Session):
    product = catalog.get_product(db, product_id)

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


def _require_category(category_id: int, db: Session):
    category = catalog.get_category(db, category_id)

    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    return category


def _validate_category(category_id: int | None, db: Session) -> None:
    if category_id is not None:
        _require_category(category_id, db)


@router.get("/products", response_model=list[ProductOut])
def list_admin_products(
    response: Response,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
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
        active_only=False,
    )
    response.headers["X-Total-Count"] = str(total)
    return products


@router.get("/products/{product_id}", response_model=ProductOut)
def get_admin_product(product_id: int, db: Session = Depends(get_db)):
    return _require_product(product_id, db)


@router.post(
    "/products",
    response_model=ProductOut,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    payload: ProductCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _validate_category(payload.category_id, db)

    try:
        return catalog.create_product(
            db, payload, actor_user_id=current_user.id
        )
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Variant SKUs and size/color combinations must be unique.",
        ) from exc


@router.post(
    "/products/import",
    response_model=CatalogImportResultOut,
)
async def import_products(
    file: UploadFile = File(...),
    dry_run: bool = Query(True),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    content = await file.read(MAX_CATALOG_IMPORT_BYTES + 1)

    if len(content) > MAX_CATALOG_IMPORT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Catalog CSV must be 2 MB or smaller.",
        )

    try:
        csv_text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Catalog CSV must be UTF-8 encoded.",
        ) from exc

    try:
        return catalog_import.import_catalog(
            db,
            csv_text,
            dry_run=dry_run,
            actor_user_id=current_user.id,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Catalog import could not be completed.",
        ) from exc


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    product = _require_product(product_id, db)

    if "category_id" in payload.model_fields_set:
        _validate_category(payload.category_id, db)

    try:
        return catalog.update_product(
            db,
            product,
            payload,
            actor_user_id=current_user.id,
        )
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Variant SKUs and size/color combinations must be unique.",
        ) from exc


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    product = _require_product(product_id, db)
    catalog.delete_product(
        db, product, actor_user_id=current_user.id
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/categories",
    response_model=CategoryOut,
    status_code=status.HTTP_201_CREATED,
)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    try:
        return catalog.create_category(db, payload.name)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with that name already exists.",
        ) from exc


@router.put("/categories/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
):
    category = _require_category(category_id, db)

    try:
        return catalog.update_category(db, category, payload.name)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with that name already exists.",
        ) from exc


@router.delete(
    "/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = _require_category(category_id, db)

    if catalog.category_has_products(db, category.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a category that still has products.",
        )

    catalog.delete_category(db, category)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
