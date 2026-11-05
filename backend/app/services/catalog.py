from collections.abc import Sequence
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import Category, Product, ProductImage, ProductVariant
from app.schemas.product import ProductCreate, ProductUpdate, ProductVariantIn
from app.services.inventory import record_stock_movement
from app.services.notifications import maybe_notify_low_stock
from app.utils.slug import unique_slug

PRODUCT_LOAD_OPTIONS = (
    joinedload(Product.category),
    selectinload(Product.images),
    selectinload(Product.variants),
)


def _product_query(filters: list):
    return select(Product).where(*filters).options(*PRODUCT_LOAD_OPTIONS)


def list_products(
    db: Session,
    *,
    page: int,
    limit: int,
    search: str | None = None,
    category: str | None = None,
    sort: str = "newest",
    active_only: bool = True,
) -> tuple[Sequence[Product], int]:
    filters = []

    if active_only:
        filters.append(Product.is_active.is_(True))
    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append(
            or_(Product.name.ilike(term), Product.description.ilike(term))
        )
    if category:
        filters.append(Product.category.has(Category.slug == category))

    total = db.scalar(select(func.count(Product.id)).where(*filters)) or 0

    stmt = _product_query(filters)

    if sort == "price_asc":
        stmt = stmt.order_by(Product.price.asc(), Product.id.asc())
    elif sort == "price_desc":
        stmt = stmt.order_by(Product.price.desc(), Product.id.asc())
    elif sort == "name":
        stmt = stmt.order_by(Product.name.asc())
    else:
        stmt = stmt.order_by(Product.created_at.desc(), Product.id.desc())

    stmt = stmt.offset((page - 1) * limit).limit(limit)
    products = db.scalars(stmt).unique().all()

    return products, total


def get_product(
    db: Session, product_id: int, *, active_only: bool = False
) -> Product | None:
    filters = [Product.id == product_id]

    if active_only:
        filters.append(Product.is_active.is_(True))

    return db.scalar(_product_query(filters))


def get_product_by_slug(
    db: Session, slug: str, *, active_only: bool = False
) -> Product | None:
    filters = [Product.slug == slug]

    if active_only:
        filters.append(Product.is_active.is_(True))

    return db.scalar(_product_query(filters))


def get_category(db: Session, category_id: int) -> Category | None:
    return db.get(Category, category_id)


def list_related_products(
    db: Session, product: Product, *, limit: int = 4
) -> list[Product]:
    """Recommend same-category products, then fill from the catalog."""

    products: list[Product] = []

    if product.category_id is not None:
        products = list(
            db.scalars(
                _product_query(
                    [
                        Product.is_active.is_(True),
                        Product.id != product.id,
                        Product.category_id == product.category_id,
                    ]
                )
                .order_by(Product.created_at.desc(), Product.id.desc())
                .limit(limit)
            ).unique().all()
        )

    if len(products) >= limit:
        return products

    excluded_ids = [product.id, *(item.id for item in products)]
    filler = db.scalars(
        _product_query(
            [
                Product.is_active.is_(True),
                Product.id.notin_(excluded_ids),
            ]
        )
        .order_by(Product.created_at.desc(), Product.id.desc())
        .limit(limit - len(products))
    ).unique().all()
    products.extend(filler)

    return products


def create_product(
    db: Session,
    payload: ProductCreate,
    *,
    actor_user_id: int | None = None,
) -> Product:
    product = Product(
        name=payload.name,
        slug=unique_slug(db, Product, payload.name),
        description=payload.description,
        price=payload.price,
        category_id=payload.category_id,
        is_active=payload.is_active,
    )
    product.images = _build_images(payload.images)
    product.variants = build_variants(payload.variants)

    db.add(product)
    db.flush()

    for variant in product.variants:
        if variant.stock <= 0:
            continue

        record_stock_movement(
            db,
            variant=variant,
            movement_type="initial_stock",
            quantity_delta=variant.stock,
            stock_before=0,
            stock_after=variant.stock,
            product_name=product.name,
            size=variant.size,
            color=variant.color,
            sku=variant.sku,
            reason="Product created.",
            actor_user_id=actor_user_id,
        )

    db.commit()

    return get_product(db, product.id)


def update_product(
    db: Session,
    product: Product,
    payload: ProductUpdate,
    *,
    actor_user_id: int | None = None,
) -> Product:
    data = payload.model_dump(exclude_unset=True, exclude={"images", "variants"})

    for field, value in data.items():
        setattr(product, field, value)

    if "images" in payload.model_fields_set:
        new_urls = payload.images or []

        if [image.url for image in product.images] != new_urls:
            product.images = _build_images(new_urls)

    if "variants" in payload.model_fields_set:
        sync_variants(
            db,
            product,
            payload.variants or [],
            actor_user_id=actor_user_id,
        )

    db.commit()

    return get_product(db, product.id)


def delete_product(
    db: Session,
    product: Product,
    *,
    actor_user_id: int | None = None,
) -> None:
    for variant in list(product.variants):
        if variant.stock <= 0:
            continue

        record_stock_movement(
            db,
            variant=variant,
            movement_type="product_deleted",
            quantity_delta=-variant.stock,
            stock_before=variant.stock,
            stock_after=0,
            product_name=product.name,
            size=variant.size,
            color=variant.color,
            sku=variant.sku,
            reason="Product deleted.",
            actor_user_id=actor_user_id,
        )

    db.flush()
    db.delete(product)
    db.commit()


def list_categories(db: Session) -> Sequence[Category]:
    return db.scalars(select(Category).order_by(Category.name.asc())).all()


def create_category(db: Session, name: str) -> Category:
    category = Category(name=name, slug=unique_slug(db, Category, name))
    db.add(category)
    db.commit()
    return category


def update_category(db: Session, category: Category, name: str) -> Category:
    category.name = name
    category.slug = unique_slug(db, Category, name, exclude_id=category.id)
    db.commit()
    return category


def category_has_products(db: Session, category_id: int) -> bool:
    count = db.scalar(
        select(func.count(Product.id)).where(Product.category_id == category_id)
    )
    return bool(count)


def delete_category(db: Session, category: Category) -> None:
    db.delete(category)
    db.commit()


def _build_images(urls: list[str]) -> list[ProductImage]:
    return [
        ProductImage(url=url, sort_order=index)
        for index, url in enumerate(urls)
    ]


def build_variants(variants: list[ProductVariantIn]) -> list[ProductVariant]:
    return [
        ProductVariant(
            size=variant.size.strip(),
            color=variant.color.strip(),
            sku=variant.sku.strip(),
            stock=variant.stock,
            low_stock_threshold=variant.low_stock_threshold,
        )
        for variant in variants
    ]


def _variant_key(size: str, color: str) -> tuple[str, str]:
    return (size.strip().lower(), color.strip().lower())


def sync_variants(
    db: Session,
    product: Product,
    incoming_variants: list[ProductVariantIn],
    *,
    actor_user_id: int | None = None,
    remove_missing: bool = True,
) -> None:
    """Update variants in place so IDs and stock history are preserved."""

    existing_by_key = {
        _variant_key(variant.size, variant.color): variant
        for variant in product.variants
    }
    existing_by_sku = {
        variant.sku.strip().lower(): variant
        for variant in product.variants
    }
    matched: list[tuple[ProductVariant, ProductVariantIn]] = []
    new_entries: list[ProductVariantIn] = []
    used_existing_ids: set[int] = set()
    incoming_keys: set[tuple[str, str]] = set()
    incoming_skus: set[str] = set()

    for incoming in incoming_variants:
        key = _variant_key(incoming.size, incoming.color)
        sku = incoming.sku.strip().lower()

        if key in incoming_keys:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Each size/color combination may appear only "
                    "once."
                ),
            )
        if sku in incoming_skus:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each variant SKU may appear only once.",
            )

        incoming_keys.add(key)
        incoming_skus.add(sku)

        existing = existing_by_key.get(key)

        if (
            existing is None
            or existing.id in used_existing_ids
        ):
            existing = existing_by_sku.get(sku)

        if (
            existing is not None
            and existing.id not in used_existing_ids
        ):
            used_existing_ids.add(existing.id)
            matched.append((existing, incoming))
        else:
            new_entries.append(incoming)

    removed = (
        [
            variant
            for variant in product.variants
            if variant.id not in used_existing_ids
        ]
        if remove_missing
        else []
    )

    for variant in removed:
        if variant.stock <= 0:
            continue

        record_stock_movement(
            db,
            variant=variant,
            movement_type="variant_removed",
            quantity_delta=-variant.stock,
            stock_before=variant.stock,
            stock_after=0,
            product_name=product.name,
            size=variant.size,
            color=variant.color,
            sku=variant.sku,
            reason="Variant removed from product.",
            actor_user_id=actor_user_id,
        )

    if removed:
        db.flush()
        for variant in removed:
            product.variants.remove(variant)
        db.flush()

    changed_skus = [
        (existing, incoming)
        for existing, incoming in matched
        if existing.sku.strip().lower()
        != incoming.sku.strip().lower()
    ]

    for existing, _incoming in changed_skus:
        existing.sku = (
            f"__tmp-{existing.id}-{uuid4().hex[:12]}"
        )

    if changed_skus:
        db.flush()

    for existing, incoming in matched:
        stock_before = existing.stock
        existing.size = incoming.size.strip()
        existing.color = incoming.color.strip()
        existing.sku = incoming.sku.strip()
        existing.stock = incoming.stock
        existing.low_stock_threshold = (
            incoming.low_stock_threshold
        )

        if existing.stock == stock_before:
            continue

        record_stock_movement(
            db,
            variant=existing,
            movement_type="manual_adjustment",
            quantity_delta=existing.stock - stock_before,
            stock_before=stock_before,
            stock_after=existing.stock,
            product_name=product.name,
            size=existing.size,
            color=existing.color,
            sku=existing.sku,
            reason="Variant updated in product editor.",
            actor_user_id=actor_user_id,
        )
        maybe_notify_low_stock(
            db,
            variant=existing,
            stock_before=stock_before,
            stock_after=existing.stock,
            product_name=product.name,
        )

    if matched:
        db.flush()

    created: list[ProductVariant] = []

    for incoming in new_entries:
        variant = ProductVariant(
            size=incoming.size.strip(),
            color=incoming.color.strip(),
            sku=incoming.sku.strip(),
            stock=incoming.stock,
            low_stock_threshold=incoming.low_stock_threshold,
        )
        product.variants.append(variant)
        created.append(variant)

    if created:
        db.flush()

        for variant in created:
            if variant.stock <= 0:
                continue

            record_stock_movement(
                db,
                variant=variant,
                movement_type="initial_stock",
                quantity_delta=variant.stock,
                stock_before=0,
                stock_after=variant.stock,
                product_name=product.name,
                size=variant.size,
                color=variant.color,
                sku=variant.sku,
                reason="Variant added to product.",
                actor_user_id=actor_user_id,
            )
