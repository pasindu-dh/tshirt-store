from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import ShippingMethod
from app.schemas.shipping import (
    ShippingMethodCreate,
    ShippingMethodUpdate,
)


def list_methods(
    db: Session, *, active_only: bool = False
) -> list[ShippingMethod]:
    filters = []

    if active_only:
        filters.append(ShippingMethod.is_active.is_(True))

    return list(
        db.scalars(
            select(ShippingMethod)
            .where(*filters)
            .order_by(
                ShippingMethod.sort_order.asc(),
                ShippingMethod.id.asc(),
            )
        ).all()
    )


def get_method(
    db: Session, method_id: int
) -> ShippingMethod | None:
    return db.get(ShippingMethod, method_id)


def get_active_method(
    db: Session, method_id: int
) -> ShippingMethod | None:
    return db.scalar(
        select(ShippingMethod).where(
            ShippingMethod.id == method_id,
            ShippingMethod.is_active.is_(True),
        )
    )


def get_default_method(
    db: Session,
) -> ShippingMethod | None:
    return db.scalar(
        select(ShippingMethod)
        .where(ShippingMethod.is_active.is_(True))
        .order_by(
            ShippingMethod.sort_order.asc(),
            ShippingMethod.id.asc(),
        )
    )


def default_fee(db: Session) -> int:
    method = get_default_method(db)

    if method is not None:
        return method.fee_lkr

    return settings.shipping_fee_lkr


def create_method(
    db: Session, payload: ShippingMethodCreate
) -> ShippingMethod:
    method = ShippingMethod(
        name=payload.name,
        description=payload.description,
        fee_lkr=payload.fee_lkr,
        is_active=payload.is_active,
        sort_order=payload.sort_order,
    )
    db.add(method)
    db.commit()
    db.refresh(method)
    return method


def update_method(
    db: Session,
    method: ShippingMethod,
    payload: ShippingMethodUpdate,
) -> ShippingMethod:
    for field, value in payload.model_dump(
        exclude_unset=True
    ).items():
        setattr(method, field, value)

    db.commit()
    db.refresh(method)
    return method


def delete_method(
    db: Session, method: ShippingMethod
) -> None:
    db.delete(method)
    db.commit()
