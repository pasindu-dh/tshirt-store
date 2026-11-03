from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import Category, Product, ProductImage, ProductVariant
from app.schemas.product import ProductCreate, ProductUpdate, ProductVariantIn
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


def get_category(db: Session, category_id: int) -> Category | None:
    return db.get(Category, category_id)


def create_product(db: Session, payload: ProductCreate) -> Product:
    product = Product(
        name=payload.name,
        slug=unique_slug(db, Product, payload.name),
        description=payload.description,
        price=payload.price,
        category_id=payload.category_id,
        is_active=payload.is_active,
    )
    product.images = _build_images(payload.images)
    product.variants = _build_variants(payload.variants)

    db.add(product)
    db.commit()

    return get_product(db, product.id)


def update_product(
    db: Session, product: Product, payload: ProductUpdate
) -> Product:
    data = payload.model_dump(exclude_unset=True, exclude={"images", "variants"})

    for field, value in data.items():
        setattr(product, field, value)

    if "images" in payload.model_fields_set:
        product.images = _build_images(payload.images or [])
    if "variants" in payload.model_fields_set:
        product.variants = _build_variants(payload.variants or [])

    db.commit()

    return get_product(db, product.id)


def delete_product(db: Session, product: Product) -> None:
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


def _build_variants(variants: list[ProductVariantIn]) -> list[ProductVariant]:
    return [
        ProductVariant(
            size=variant.size,
            color=variant.color,
            sku=variant.sku,
            stock=variant.stock,
        )
        for variant in variants
    ]
