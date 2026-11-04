import csv
import io
from collections import OrderedDict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Category,
    Product,
    ProductImage,
    ProductVariant,
)
from app.schemas.catalog_import import (
    CatalogImportResultOut,
    CatalogImportRowOut,
    CatalogImportSummaryOut,
)
from app.schemas.product import ProductVariantIn
from app.services import catalog
from app.services.inventory import record_stock_movement
from app.utils.slug import unique_slug

MAX_IMPORT_ROWS = 5000

CATALOG_HEADERS = [
    "product_slug",
    "product_name",
    "description",
    "price",
    "category_slug",
    "is_active",
    "image_urls",
    "variant_size",
    "variant_color",
    "variant_sku",
    "variant_stock",
    "variant_low_stock_threshold",
]


def _result(
    *,
    dry_run: bool,
    rows: list[CatalogImportRowOut],
    total_rows: int,
    error_rows: int,
    products_create: int = 0,
    products_update: int = 0,
    variants_create: int = 0,
    variants_update: int = 0,
) -> CatalogImportResultOut:
    return CatalogImportResultOut(
        dry_run=dry_run,
        valid=error_rows == 0,
        summary=CatalogImportSummaryOut(
            total_rows=total_rows,
            valid_rows=max(0, total_rows - error_rows),
            error_rows=error_rows,
            products_create=products_create,
            products_update=products_update,
            variants_create=variants_create,
            variants_update=variants_update,
        ),
        rows=rows,
    )


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _parse_int(
    value: str, field: str, minimum: int = 0
) -> tuple[int | None, str | None]:
    try:
        number = int(_clean(value))
    except (TypeError, ValueError):
        return None, f"{field} must be a whole number."

    if number < minimum:
        return None, f"{field} must be at least {minimum}."

    return number, None


def _parse_bool(value: str) -> tuple[bool | None, str | None]:
    normalized = _clean(value).lower()

    if normalized in {"", "true", "1", "yes", "y"}:
        return True, None

    if normalized in {"false", "0", "no", "n"}:
        return False, None

    return None, "is_active must be true or false."


def _variant_label(size: str, color: str) -> str:
    return f"{size} / {color}"


def _row_error(
    row: int,
    name: str,
    slug: str,
    variant: str,
    message: str,
) -> CatalogImportRowOut:
    return CatalogImportRowOut(
        row=row,
        action="error",
        product_name=name,
        product_slug=slug,
        variant=variant,
        message=message,
    )


def import_catalog(
    db: Session,
    csv_text: str,
    *,
    dry_run: bool,
    actor_user_id: int | None = None,
) -> CatalogImportResultOut:
    reader = csv.DictReader(io.StringIO(csv_text))
    fieldnames = [
        (field or "").strip()
        for field in (reader.fieldnames or [])
    ]
    missing = [
        header
        for header in CATALOG_HEADERS
        if header not in fieldnames
    ]

    if missing:
        headers = ", ".join(missing)
        return _result(
            dry_run=dry_run,
            rows=[
                _row_error(
                    1,
                    "",
                    "",
                    "",
                    f"Missing required column(s): {headers}.",
                )
            ],
            total_rows=0,
            error_rows=1,
        )

    categories = {
        category.slug.lower(): category
        for category in db.scalars(select(Category)).all()
    }
    existing_products = db.scalars(
        select(Product).options(
            selectinload(Product.variants),
            selectinload(Product.images),
        )
    ).all()
    products_by_slug = {
        product.slug.lower(): product
        for product in existing_products
    }
    variants_by_sku = {
        variant.sku.lower(): (product, variant)
        for product in existing_products
        for variant in product.variants
    }

    groups: OrderedDict[str, dict] = OrderedDict()
    result_rows: list[CatalogImportRowOut] = []
    sku_seen: dict[str, tuple[str, tuple[str, str]]] = {}
    total_rows = 0
    error_rows = 0

    for raw in reader:
        row = {
            (key or "").strip(): (value or "").strip()
            for key, value in raw.items()
        }
        total_rows += 1

        if total_rows > MAX_IMPORT_ROWS:
            return _result(
                dry_run=dry_run,
                rows=result_rows
                + [
                    _row_error(
                        total_rows,
                        "",
                        "",
                        "",
                        (
                            "Import exceeds the maximum of "
                            f"{MAX_IMPORT_ROWS} rows."
                        ),
                    )
                ],
                total_rows=total_rows,
                error_rows=error_rows + 1,
            )

        row_number = total_rows + 1

        if not any(row.values()):
            total_rows -= 1
            continue

        product_slug = _clean(
            row.get("product_slug")
        ).lower()
        product_name = _clean(row.get("product_name"))

        if not product_name:
            result_rows.append(
                _row_error(
                    row_number,
                    "",
                    product_slug,
                    "",
                    "product_name is required.",
                )
            )
            error_rows += 1
            continue

        if len(product_name) > 160:
            result_rows.append(
                _row_error(
                    row_number,
                    product_name,
                    product_slug,
                    "",
                    "product_name is too long.",
                )
            )
            error_rows += 1
            continue

        description = _clean(row.get("description"))
        price, error = _parse_int(
            row.get("price", ""), "price"
        )

        if error:
            result_rows.append(
                _row_error(
                    row_number,
                    product_name,
                    product_slug,
                    "",
                    error,
                )
            )
            error_rows += 1
            continue

        category_slug = _clean(
            row.get("category_slug")
        ).lower()
        category = (
            categories.get(category_slug)
            if category_slug
            else None
        )

        if category_slug and category is None:
            result_rows.append(
                _row_error(
                    row_number,
                    product_name,
                    product_slug,
                    "",
                    (
                        f"Unknown category_slug "
                        f"'{category_slug}'."
                    ),
                )
            )
            error_rows += 1
            continue

        is_active, error = _parse_bool(
            row.get("is_active", "")
        )

        if error:
            result_rows.append(
                _row_error(
                    row_number,
                    product_name,
                    product_slug,
                    "",
                    error,
                )
            )
            error_rows += 1
            continue

        image_urls = [
            value.strip()
            for value in _clean(
                row.get("image_urls")
            ).split("|")
            if value.strip()
        ]

        if len(image_urls) > 10:
            result_rows.append(
                _row_error(
                    row_number,
                    product_name,
                    product_slug,
                    "",
                    "image_urls supports at most 10 images.",
                )
            )
            error_rows += 1
            continue

        if any(len(url) > 500 for url in image_urls):
            result_rows.append(
                _row_error(
                    row_number,
                    product_name,
                    product_slug,
                    "",
                    "Each image URL must be 500 characters or fewer.",
                )
            )
            error_rows += 1
            continue

        size = _clean(row.get("variant_size"))
        color = _clean(row.get("variant_color"))
        sku = _clean(row.get("variant_sku"))
        stock, error = _parse_int(
            row.get("variant_stock", ""),
            "variant_stock",
        )

        if error:
            result_rows.append(
                _row_error(
                    row_number,
                    product_name,
                    product_slug,
                    _variant_label(size, color),
                    error,
                )
            )
            error_rows += 1
            continue

        threshold_value = _clean(
            row.get("variant_low_stock_threshold")
        )
        threshold, error = _parse_int(
            threshold_value or "5",
            "variant_low_stock_threshold",
        )

        if error:
            result_rows.append(
                _row_error(
                    row_number,
                    product_name,
                    product_slug,
                    _variant_label(size, color),
                    error,
                )
            )
            error_rows += 1
            continue

        if not size or len(size) > 20:
            result_rows.append(
                _row_error(
                    row_number,
                    product_name,
                    product_slug,
                    _variant_label(size, color),
                    "variant_size is required and must be 20 characters or fewer.",
                )
            )
            error_rows += 1
            continue

        if not color or len(color) > 40:
            result_rows.append(
                _row_error(
                    row_number,
                    product_name,
                    product_slug,
                    _variant_label(size, color),
                    "variant_color is required and must be 40 characters or fewer.",
                )
            )
            error_rows += 1
            continue

        if not sku or len(sku) > 80:
            result_rows.append(
                _row_error(
                    row_number,
                    product_name,
                    product_slug,
                    _variant_label(size, color),
                    "variant_sku is required and must be 80 characters or fewer.",
                )
            )
            error_rows += 1
            continue

        existing = (
            products_by_slug.get(product_slug)
            if product_slug
            else None
        )

        if product_slug and existing is None:
            result_rows.append(
                _row_error(
                    row_number,
                    product_name,
                    product_slug,
                    _variant_label(size, color),
                    (
                        f"Product slug '{product_slug}' was not "
                        "found. Leave product_slug blank to create "
                        "a new product."
                    ),
                )
            )
            error_rows += 1
            continue

        group_key = (
            f"slug:{product_slug}"
            if existing is not None
            else f"name:{product_name.lower()}"
        )
        group = groups.get(group_key)

        product_values = (
            product_name,
            description,
            price,
            category.id if category else None,
            is_active,
            tuple(image_urls),
        )

        if group is not None and group["values"] != product_values:
            result_rows.append(
                _row_error(
                    row_number,
                    product_name,
                    product_slug,
                    _variant_label(size, color),
                    (
                        "Product-level fields must match for every "
                        "row of the same product."
                    ),
                )
            )
            error_rows += 1
            continue

        if group is None:
            group = {
                "product_slug": product_slug,
                "product_name": product_name,
                "description": description,
                "price": price,
                "category_id": (
                    category.id if category else None
                ),
                "is_active": is_active,
                "images": image_urls,
                "existing": existing,
                "values": product_values,
                "variants": [],
            }
            groups[group_key] = group

        variant_key = (
            size.lower(),
            color.lower(),
        )

        if any(
            (
                variant["size"].lower(),
                variant["color"].lower(),
            )
            == variant_key
            for variant in group["variants"]
        ):
            result_rows.append(
                _row_error(
                    row_number,
                    product_name,
                    product_slug,
                    _variant_label(size, color),
                    "Duplicate size/color variant in this product.",
                )
            )
            error_rows += 1
            continue

        sku_key = sku.lower()
        seen = sku_seen.get(sku_key)

        if seen is not None and seen != (
            group_key,
            variant_key,
        ):
            result_rows.append(
                _row_error(
                    row_number,
                    product_name,
                    product_slug,
                    _variant_label(size, color),
                    "Duplicate variant SKU in this import.",
                )
            )
            error_rows += 1
            continue

        owner = variants_by_sku.get(sku_key)

        if owner is not None:
            owner_product, owner_variant = owner
            allowed = (
                existing is not None
                and owner_product.id == existing.id
                and (
                    owner_variant.size.lower(),
                    owner_variant.color.lower(),
                )
                == variant_key
            )

            if not allowed:
                result_rows.append(
                    _row_error(
                        row_number,
                        product_name,
                        product_slug,
                        _variant_label(size, color),
                        (
                            "This SKU already belongs to another "
                            "product or variant."
                        ),
                    )
                )
                error_rows += 1
                continue

        sku_seen[sku_key] = (group_key, variant_key)

        existing_variant = None

        if existing is not None:
            existing_variant = next(
                (
                    variant
                    for variant in existing.variants
                    if (
                        variant.size.lower(),
                        variant.color.lower(),
                    )
                    == variant_key
                ),
                None,
            )

        action = (
            "update" if existing_variant is not None else "create"
        )
        group["variants"].append(
            {
                "size": size,
                "color": color,
                "sku": sku,
                "stock": stock,
                "low_stock_threshold": threshold,
            }
        )
        result_rows.append(
            CatalogImportRowOut(
                row=row_number,
                action=action,
                product_name=product_name,
                product_slug=(
                    existing.slug if existing is not None else ""
                ),
                variant=_variant_label(size, color),
                message=(
                    f"Variant will be {action}d."
                    if dry_run
                    else f"Variant {action}d."
                ),
            )
        )

    products_create = sum(
        1
        for group in groups.values()
        if group["existing"] is None
    )
    products_update = len(groups) - products_create
    variants_create = sum(
        1
        for group in groups.values()
        for variant in group["variants"]
        if variant["sku"].lower()
        not in {
            existing_variant.sku.lower()
            for existing_variant in (
                group["existing"].variants
                if group["existing"] is not None
                else []
            )
        }
    )
    variants_update = sum(
        len(group["variants"])
        for group in groups.values()
    ) - variants_create

    if dry_run or error_rows > 0:
        return _result(
            dry_run=dry_run,
            rows=result_rows,
            total_rows=total_rows,
            error_rows=error_rows,
            products_create=products_create,
            products_update=products_update,
            variants_create=variants_create,
            variants_update=variants_update,
        )

    try:
        for group in groups.values():
            incoming = [
                ProductVariantIn(
                    size=variant["size"],
                    color=variant["color"],
                    sku=variant["sku"],
                    stock=variant["stock"],
                    low_stock_threshold=variant[
                        "low_stock_threshold"
                    ],
                )
                for variant in group["variants"]
            ]
            existing = group["existing"]

            if existing is not None:
                existing.name = group["product_name"]
                existing.description = group["description"]
                existing.price = group["price"]
                existing.category_id = group["category_id"]
                existing.is_active = group["is_active"]

                if [
                    image.url for image in existing.images
                ] != group["images"]:
                    existing.images = [
                        ProductImage(url=url, sort_order=index)
                        for index, url in enumerate(
                            group["images"]
                        )
                    ]

                catalog.sync_variants(
                    db,
                    existing,
                    incoming,
                    actor_user_id=actor_user_id,
                    remove_missing=False,
                )
            else:
                product = Product(
                    name=group["product_name"],
                    slug=unique_slug(
                        db, Product, group["product_name"]
                    ),
                    description=group["description"],
                    price=group["price"],
                    category_id=group["category_id"],
                    is_active=group["is_active"],
                )
                product.images = [
                    ProductImage(url=url, sort_order=index)
                    for index, url in enumerate(
                        group["images"]
                    )
                ]
                product.variants = catalog.build_variants(
                    incoming
                )
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
                        reason="Product imported.",
                        actor_user_id=actor_user_id,
                    )

        db.commit()
    except Exception:
        db.rollback()
        raise

    return _result(
        dry_run=False,
        rows=result_rows,
        total_rows=total_rows,
        error_rows=0,
        products_create=products_create,
        products_update=products_update,
        variants_create=variants_create,
        variants_update=variants_update,
    )
