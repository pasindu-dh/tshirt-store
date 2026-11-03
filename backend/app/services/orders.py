from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.models import (
    CartItem,
    Order,
    OrderItem,
    Product,
    ProductVariant,
    User,
)
from app.schemas.order import OrderCreate


def get_orders(db: Session, user_id: int) -> list[Order]:
    return list(
        db.scalars(
            select(Order)
            .where(Order.user_id == user_id)
            .options(selectinload(Order.items))
            .order_by(Order.created_at.desc(), Order.id.desc())
        ).all()
    )


def get_order(
    db: Session, user_id: int, order_id: int
) -> Order | None:
    return db.scalar(
        select(Order)
        .where(Order.id == order_id, Order.user_id == user_id)
        .options(selectinload(Order.items))
    )


def create_order(
    db: Session, user: User, payload: OrderCreate
) -> Order:
    cart_items = list(
        db.scalars(
            select(CartItem)
            .where(CartItem.user_id == user.id)
            .order_by(CartItem.id)
        ).all()
    )

    if not cart_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your cart is empty",
        )

    variant_ids = sorted({item.variant_id for item in cart_items})
    locked_variants = db.scalars(
        select(ProductVariant)
        .where(ProductVariant.id.in_(variant_ids))
        .order_by(ProductVariant.id)
        .with_for_update()
        .options(
            selectinload(ProductVariant.product).selectinload(
                Product.images
            )
        )
    ).all()
    variants_by_id = {variant.id: variant for variant in locked_variants}

    for item in cart_items:
        variant = variants_by_id.get(item.variant_id)

        if variant is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A product in your cart is no longer available",
            )

        if not variant.product.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{variant.product.name} is no longer available",
            )

        if variant.stock < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Only {variant.stock} of {variant.product.name} "
                    f"({variant.size}/{variant.color}) available"
                ),
            )

    subtotal = sum(
        variants_by_id[item.variant_id].product.price * item.quantity
        for item in cart_items
    )
    shipping_fee = settings.shipping_fee_lkr
    total = subtotal + shipping_fee

    order = Order(
        user_id=user.id,
        status="pending",
        payment_method=payload.payment_method,
        payment_status="pending",
        subtotal=subtotal,
        shipping_fee=shipping_fee,
        total=total,
        contact_name=payload.contact_name,
        contact_email=user.email,
        phone=payload.phone,
        address_line1=payload.address_line1,
        address_line2=payload.address_line2,
        city=payload.city,
        postal_code=payload.postal_code,
        country=payload.country,
        notes=payload.notes,
    )

    for item in cart_items:
        variant = variants_by_id[item.variant_id]
        product = variant.product
        image = product.images[0].url if product.images else ""

        order.items.append(
            OrderItem(
                product_id=product.id,
                variant_id=variant.id,
                product_name=product.name,
                product_slug=product.slug,
                image=image,
                size=variant.size,
                color=variant.color,
                sku=variant.sku,
                unit_price=product.price,
                quantity=item.quantity,
                line_total=product.price * item.quantity,
            )
        )
        variant.stock -= item.quantity
        db.delete(item)

    db.add(order)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    created = get_order(db, user.id, order.id)

    if created is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Order could not be loaded after creation",
        )

    return created
