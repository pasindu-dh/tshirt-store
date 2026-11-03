from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Coupon
from app.models.common import utcnow
from app.schemas.coupon import (
    CouponCreate,
    CouponPreviewOut,
    CouponUpdate,
)
from app.services import cart as cart_service


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def calculate_discount(coupon: Coupon, subtotal: int) -> int:
    if coupon.discount_type == "percent":
        discount = subtotal * coupon.value // 100
    else:
        discount = coupon.value

    return max(0, min(discount, subtotal))


def validate_coupon(
    db: Session,
    code: str,
    subtotal: int,
    *,
    lock: bool = False,
) -> Coupon:
    from fastapi import HTTPException, status

    normalized = code.strip().upper()

    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enter a coupon code.",
        )

    stmt = select(Coupon).where(Coupon.code == normalized)

    if lock:
        stmt = stmt.with_for_update()

    coupon = db.scalar(stmt)

    if coupon is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coupon code is not valid.",
        )

    now = utcnow()

    if not coupon.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This coupon is not active.",
        )

    if coupon.starts_at is not None and now < _as_utc(coupon.starts_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This coupon is not active yet.",
        )

    if coupon.expires_at is not None and now > _as_utc(coupon.expires_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This coupon has expired.",
        )

    if (
        coupon.usage_limit is not None
        and coupon.used_count >= coupon.usage_limit
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This coupon has reached its usage limit.",
        )

    if subtotal < coupon.min_subtotal:
        remaining = coupon.min_subtotal - subtotal
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Add LKR {remaining} more to use this coupon."
            ),
        )

    return coupon


def preview(
    db: Session, user_id: int, code: str
) -> CouponPreviewOut:
    from fastapi import HTTPException, status

    cart = cart_service.get_cart(db, user_id)

    if not cart.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your cart is empty.",
        )

    coupon = validate_coupon(db, code, cart.subtotal)
    discount_amount = calculate_discount(coupon, cart.subtotal)

    return CouponPreviewOut(
        code=coupon.code,
        description=coupon.description,
        discount_type=coupon.discount_type,
        value=coupon.value,
        discount_amount=discount_amount,
        subtotal=cart.subtotal,
        shipping_fee=cart.shipping_fee,
        total=cart.subtotal - discount_amount + cart.shipping_fee,
    )


def list_coupons(db: Session) -> list[Coupon]:
    return list(
        db.scalars(
            select(Coupon).order_by(
                Coupon.created_at.desc(), Coupon.id.desc()
            )
        ).all()
    )


def get_coupon(db: Session, coupon_id: int) -> Coupon | None:
    return db.get(Coupon, coupon_id)


def create_coupon(db: Session, payload: CouponCreate) -> Coupon:
    from fastapi import HTTPException, status

    coupon = Coupon(
        code=payload.code,
        description=payload.description,
        discount_type=payload.discount_type,
        value=payload.value,
        min_subtotal=payload.min_subtotal,
        usage_limit=payload.usage_limit,
        starts_at=payload.starts_at,
        expires_at=payload.expires_at,
        is_active=payload.is_active,
    )
    db.add(coupon)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A coupon with that code already exists.",
        ) from exc

    db.refresh(coupon)
    return coupon


def update_coupon(
    db: Session, coupon: Coupon, payload: CouponUpdate
) -> Coupon:
    from fastapi import HTTPException, status

    data = payload.model_dump(exclude_unset=True)

    # Null on these fields means "leave unchanged" for a partial update.
    for field in (
        "code",
        "description",
        "discount_type",
        "value",
        "min_subtotal",
        "is_active",
    ):
        if field in data and data[field] is None:
            data.pop(field)

    if "discount_type" in data or "value" in data:
        next_type = data.get("discount_type", coupon.discount_type)
        next_value = data.get("value", coupon.value)

        if next_type == "percent" and next_value > 100:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Percentage discounts cannot exceed 100.",
            )

    if "usage_limit" in data and data["usage_limit"] is not None:
        if data["usage_limit"] < coupon.used_count:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Usage limit cannot be lower than the number "
                    "of times the coupon has been used."
                ),
            )

    starts_at = data.get("starts_at", coupon.starts_at)
    expires_at = data.get("expires_at", coupon.expires_at)

    if (
        starts_at is not None
        and expires_at is not None
        and _as_utc(expires_at) <= _as_utc(starts_at)
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Expiry must be after the start date.",
        )

    for field, value in data.items():
        setattr(coupon, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A coupon with that code already exists.",
        ) from exc

    db.refresh(coupon)
    return coupon


def delete_coupon(db: Session, coupon: Coupon) -> None:
    db.delete(coupon)
    db.commit()
