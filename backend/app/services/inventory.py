from datetime import date, datetime, time, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Product, ProductVariant, StockMovement
from app.schemas.inventory import (
    LowStockVariantOut,
    StockAdjustmentRequest,
)
from app.services.notifications import maybe_notify_low_stock


def record_stock_movement(
    db: Session,
    *,
    variant: ProductVariant,
    movement_type: str,
    quantity_delta: int,
    stock_before: int,
    stock_after: int,
    product_name: str,
    size: str,
    color: str,
    sku: str,
    reason: str = "",
    product_id: int | None = None,
    order_id: int | None = None,
    return_request_id: int | None = None,
    actor_user_id: int | None = None,
) -> StockMovement:
    movement = StockMovement(
        variant_id=variant.id,
        product_id=(
            product_id
            if product_id is not None
            else variant.product_id
        ),
        order_id=order_id,
        return_request_id=return_request_id,
        actor_user_id=actor_user_id,
        movement_type=movement_type,
        quantity_delta=quantity_delta,
        stock_before=stock_before,
        stock_after=stock_after,
        product_name=product_name,
        size=size,
        color=color,
        sku=sku,
        reason=reason,
    )
    db.add(movement)
    return movement


def low_stock_variant_out(
    variant: ProductVariant,
) -> LowStockVariantOut:
    product = variant.product
    image = product.images[0].url if product.images else ""

    return LowStockVariantOut(
        id=variant.id,
        product_id=variant.product_id,
        product_name=product.name,
        product_slug=product.slug,
        image=image,
        size=variant.size,
        color=variant.color,
        sku=variant.sku,
        stock=variant.stock,
        low_stock_threshold=variant.low_stock_threshold,
    )


def list_low_stock(
    db: Session,
    *,
    page: int,
    limit: int,
    search: str | None = None,
) -> tuple[list[LowStockVariantOut], int]:
    filters = [
        Product.is_active.is_(True),
        ProductVariant.stock
        <= ProductVariant.low_stock_threshold,
    ]

    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Product.name.ilike(term),
                ProductVariant.sku.ilike(term),
                ProductVariant.size.ilike(term),
                ProductVariant.color.ilike(term),
            )
        )

    total = int(
        db.scalar(
            select(func.count(ProductVariant.id))
            .join(Product)
            .where(*filters)
        )
        or 0
    )
    variants = db.scalars(
        select(ProductVariant)
        .join(Product)
        .where(*filters)
        .options(
            selectinload(ProductVariant.product).selectinload(
                Product.images
            )
        )
        .order_by(
            ProductVariant.stock.asc(),
            Product.name.asc(),
            ProductVariant.id.asc(),
        )
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    return [
        low_stock_variant_out(variant)
        for variant in variants
    ], total


def list_movements(
    db: Session,
    *,
    page: int,
    limit: int,
    movement_type: str | None = None,
    variant_id: int | None = None,
    product_id: int | None = None,
    order_id: int | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[list[StockMovement], int]:
    filters = []

    if movement_type:
        filters.append(
            StockMovement.movement_type == movement_type
        )
    if variant_id is not None:
        filters.append(StockMovement.variant_id == variant_id)
    if product_id is not None:
        filters.append(StockMovement.product_id == product_id)
    if order_id is not None:
        filters.append(StockMovement.order_id == order_id)
    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                StockMovement.product_name.ilike(term),
                StockMovement.sku.ilike(term),
                StockMovement.reason.ilike(term),
            )
        )
    if date_from is not None:
        filters.append(
            StockMovement.created_at
            >= datetime.combine(date_from, time.min)
        )
    if date_to is not None:
        filters.append(
            StockMovement.created_at
            < datetime.combine(
                date_to + timedelta(days=1), time.min
            )
        )

    total = int(
        db.scalar(
            select(func.count(StockMovement.id)).where(*filters)
        )
        or 0
    )
    movements = db.scalars(
        select(StockMovement)
        .where(*filters)
        .order_by(
            StockMovement.created_at.desc(),
            StockMovement.id.desc(),
        )
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    return list(movements), total


def adjust_stock(
    db: Session,
    variant_id: int,
    payload: StockAdjustmentRequest,
    *,
    actor_user_id: int | None = None,
) -> tuple[ProductVariant, StockMovement]:
    variant = db.scalar(
        select(ProductVariant)
        .where(ProductVariant.id == variant_id)
        .with_for_update()
    )

    if variant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product variant not found.",
        )

    new_stock = variant.stock + payload.quantity_delta

    if new_stock < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Stock cannot go below zero; only "
                f"{variant.stock} unit(s) are available."
            ),
        )

    product = db.get(Product, variant.product_id)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    stock_before = variant.stock
    variant.stock = new_stock
    movement = record_stock_movement(
        db,
        variant=variant,
        movement_type="manual_adjustment",
        quantity_delta=payload.quantity_delta,
        stock_before=stock_before,
        stock_after=new_stock,
        product_name=product.name,
        size=variant.size,
        color=variant.color,
        sku=variant.sku,
        reason=payload.reason.strip(),
        actor_user_id=actor_user_id,
    )
    maybe_notify_low_stock(
        db,
        variant=variant,
        stock_before=stock_before,
        stock_after=new_stock,
        product_name=product.name,
    )
    db.commit()

    refreshed = db.scalar(
        select(ProductVariant)
        .where(ProductVariant.id == variant.id)
        .options(
            selectinload(ProductVariant.product).selectinload(
                Product.images
            )
        )
    )
    db.refresh(movement)

    return refreshed or variant, movement
