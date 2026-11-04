from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import AdminNotification, ProductVariant
from app.models.common import utcnow


def create_notification(
    db: Session,
    *,
    notification_type: str,
    title: str,
    message: str,
    link: str = "",
) -> AdminNotification:
    notification = AdminNotification(
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
    )
    db.add(notification)
    return notification


def maybe_notify_low_stock(
    db: Session,
    *,
    variant: ProductVariant,
    stock_before: int,
    stock_after: int,
    product_name: str,
) -> AdminNotification | None:
    threshold = variant.low_stock_threshold

    if not (
        stock_before > threshold
        and stock_after <= threshold
    ):
        return None

    if stock_after <= 0:
        title = f"Out of stock: {product_name}"
    else:
        title = f"Low stock: {product_name}"

    return create_notification(
        db,
        notification_type="low_stock",
        title=title,
        message=(
            f"{variant.size}/{variant.color} ({variant.sku}) "
            f"has {stock_after} left; alert threshold is "
            f"{threshold}."
        ),
        link="/admin/inventory",
    )


def list_notifications(
    db: Session,
    *,
    page: int,
    limit: int,
    unread_only: bool = False,
) -> tuple[list[AdminNotification], int]:
    filters = []

    if unread_only:
        filters.append(AdminNotification.is_read.is_(False))

    total = int(
        db.scalar(
            select(func.count(AdminNotification.id)).where(
                *filters
            )
        )
        or 0
    )
    notifications = db.scalars(
        select(AdminNotification)
        .where(*filters)
        .order_by(
            AdminNotification.created_at.desc(),
            AdminNotification.id.desc(),
        )
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    return list(notifications), total


def unread_count(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count(AdminNotification.id)).where(
                AdminNotification.is_read.is_(False)
            )
        )
        or 0
    )


def mark_read(
    db: Session, notification_id: int
) -> AdminNotification | None:
    notification = db.get(
        AdminNotification, notification_id
    )

    if notification is None:
        return None

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = utcnow()
        db.commit()
        db.refresh(notification)

    return notification


def mark_all_read(db: Session) -> int:
    result = db.execute(
        update(AdminNotification)
        .where(AdminNotification.is_read.is_(False))
        .values(is_read=True, read_at=utcnow())
    )
    db.commit()
    return int(result.rowcount or 0)
