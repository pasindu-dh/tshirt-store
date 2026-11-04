from datetime import timedelta

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
from app.models.common import utcnow
from app.schemas.order import OrderCreate
from app.services import coupons as coupon_service
from app.services import shipping as shipping_service
from app.services.inventory import record_stock_movement
from app.services.notifications import (
    create_notification,
    maybe_notify_low_stock,
)


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
    if (
        payload.payment_method == "online"
        and not settings.online_payments_enabled
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Online payment is not available.",
        )

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
    coupon = None
    discount_amount = 0

    if payload.coupon_code.strip():
        coupon = coupon_service.validate_coupon(
            db, payload.coupon_code, subtotal, lock=True
        )
        discount_amount = coupon_service.calculate_discount(
            coupon, subtotal
        )

    if payload.shipping_method_id is not None:
        shipping_method = shipping_service.get_active_method(
            db, payload.shipping_method_id
        )

        if shipping_method is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "The selected shipping method is not "
                    "available."
                ),
            )
    else:
        shipping_method = shipping_service.get_default_method(db)

    shipping_fee = (
        shipping_method.fee_lkr
        if shipping_method is not None
        else settings.shipping_fee_lkr
    )
    shipping_method_name = (
        shipping_method.name
        if shipping_method is not None
        else "Standard Delivery"
    )
    total = subtotal - discount_amount + shipping_fee
    reservation_expires_at = None

    if (
        payload.payment_method == "online"
        and settings.online_payment_reservation_minutes > 0
    ):
        reservation_expires_at = utcnow() + timedelta(
            minutes=settings.online_payment_reservation_minutes
        )

    order = Order(
        user_id=user.id,
        status="pending",
        payment_method=payload.payment_method,
        payment_status="pending",
        subtotal=subtotal,
        shipping_method_id=(
            shipping_method.id
            if shipping_method is not None
            else None
        ),
        shipping_method_name=shipping_method_name,
        shipping_fee=shipping_fee,
        discount_code=coupon.code if coupon is not None else "",
        discount_amount=discount_amount,
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
        reservation_expires_at=reservation_expires_at,
    )

    stock_entries = []

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
        stock_before = variant.stock
        variant.stock -= item.quantity
        stock_entries.append(
            (
                variant,
                product.name,
                stock_before,
                variant.stock,
            )
        )
        db.delete(item)

    db.add(order)

    try:
        db.flush()

        for (
            variant,
            product_name,
            stock_before,
            stock_after,
        ) in stock_entries:
            record_stock_movement(
                db,
                variant=variant,
                movement_type="order_placed",
                quantity_delta=stock_after - stock_before,
                stock_before=stock_before,
                stock_after=stock_after,
                product_name=product_name,
                size=variant.size,
                color=variant.color,
                sku=variant.sku,
                reason=f"Order #{order.id} placed.",
                order_id=order.id,
            )
            maybe_notify_low_stock(
                db,
                variant=variant,
                stock_before=stock_before,
                stock_after=stock_after,
                product_name=product_name,
            )

        create_notification(
            db,
            notification_type="new_order",
            title=f"New order #{order.id}",
            message=(
                f"{order.contact_name} placed an order for "
                f"LKR {order.total}."
            ),
            link=f"/admin/orders/{order.id}",
        )

        if coupon is not None:
            coupon.used_count += 1

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
