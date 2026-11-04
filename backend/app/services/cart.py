from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models import CartItem, Product, ProductVariant
from app.schemas.cart import CartItemOut, CartMergeRequest, CartOut
from app.services import shipping as shipping_service


def _cart_query(user_id: int):
    return (
        select(CartItem)
        .where(CartItem.user_id == user_id)
        .options(
            selectinload(CartItem.variant)
            .selectinload(ProductVariant.product)
            .selectinload(Product.images)
        )
        .order_by(CartItem.id)
    )


def _to_out(item: CartItem) -> CartItemOut:
    variant = item.variant
    product = variant.product
    image = product.images[0].url if product.images else ""

    return CartItemOut(
        id=item.id,
        variant_id=variant.id,
        product_id=product.id,
        product_name=product.name,
        product_slug=product.slug,
        image=image,
        price=product.price,
        size=variant.size,
        color=variant.color,
        sku=variant.sku,
        stock=variant.stock,
        quantity=item.quantity,
        line_total=product.price * item.quantity,
    )


def get_cart(db: Session, user_id: int) -> CartOut:
    items = db.scalars(_cart_query(user_id)).all()
    out_items = [_to_out(item) for item in items]
    subtotal = sum(item.line_total for item in out_items)
    shipping_fee = (
        shipping_service.default_fee(db) if out_items else 0
    )

    return CartOut(
        items=out_items,
        item_count=sum(item.quantity for item in out_items),
        subtotal=subtotal,
        shipping_fee=shipping_fee,
        total=subtotal + shipping_fee,
    )


def _get_variant(db: Session, variant_id: int) -> ProductVariant:
    variant = db.scalar(
        select(ProductVariant)
        .where(ProductVariant.id == variant_id)
        .options(selectinload(ProductVariant.product))
    )

    if variant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product variant not found",
        )

    if not variant.product.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This product is not available",
        )

    return variant


def add_item(
    db: Session, user_id: int, variant_id: int, quantity: int
) -> CartOut:
    variant = _get_variant(db, variant_id)

    if variant.stock <= 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This variant is out of stock",
        )

    item = db.scalar(
        select(CartItem).where(
            CartItem.user_id == user_id,
            CartItem.variant_id == variant_id,
        )
    )
    desired = (item.quantity if item else 0) + quantity

    if desired > variant.stock:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only {variant.stock} item(s) available",
        )

    if item is not None:
        item.quantity = desired
    else:
        db.add(
            CartItem(
                user_id=user_id,
                variant_id=variant_id,
                quantity=desired,
            )
        )

    db.commit()
    return get_cart(db, user_id)


def update_item(
    db: Session, user_id: int, item_id: int, quantity: int
) -> CartOut:
    item = db.scalar(
        select(CartItem)
        .where(CartItem.id == item_id, CartItem.user_id == user_id)
        .options(
            selectinload(CartItem.variant).selectinload(
                ProductVariant.product
            )
        )
    )

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found",
        )

    variant = item.variant

    if not variant.product.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This product is not available",
        )

    if quantity > variant.stock:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only {variant.stock} item(s) available",
        )

    item.quantity = quantity
    db.commit()
    return get_cart(db, user_id)


def remove_item(db: Session, user_id: int, item_id: int) -> CartOut:
    item = db.scalar(
        select(CartItem).where(
            CartItem.id == item_id, CartItem.user_id == user_id
        )
    )

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found",
        )

    db.delete(item)
    db.commit()
    return get_cart(db, user_id)


def clear_cart(db: Session, user_id: int) -> CartOut:
    db.execute(delete(CartItem).where(CartItem.user_id == user_id))
    db.commit()
    return get_cart(db, user_id)


def merge_cart(
    db: Session, user_id: int, payload: CartMergeRequest
) -> CartOut:
    quantities: dict[int, int] = {}

    for entry in payload.items:
        quantities[entry.variant_id] = min(
            99, quantities.get(entry.variant_id, 0) + entry.quantity
        )

    for variant_id, requested in quantities.items():
        variant = db.scalar(
            select(ProductVariant)
            .where(ProductVariant.id == variant_id)
            .options(selectinload(ProductVariant.product))
        )

        if (
            variant is None
            or not variant.product.is_active
            or variant.stock <= 0
        ):
            continue

        item = db.scalar(
            select(CartItem).where(
                CartItem.user_id == user_id,
                CartItem.variant_id == variant_id,
            )
        )
        desired = (item.quantity if item else 0) + requested
        capped = min(desired, variant.stock)

        if capped <= 0:
            continue

        if item is not None:
            item.quantity = capped
        else:
            db.add(
                CartItem(
                    user_id=user_id,
                    variant_id=variant_id,
                    quantity=capped,
                )
            )

    db.commit()
    return get_cart(db, user_id)
