from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AdminNotification, ProductVariant, User
from app.models.common import utcnow
from app.services.email import send_admin_alert

_executor: ThreadPoolExecutor | None = None
_executor_lock = Lock()


def _alert_executor() -> ThreadPoolExecutor:
    global _executor

    with _executor_lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="furzy-admin-alert",
            )

        return _executor


def admin_alert_recipients(db: Session) -> list[str]:
    configured = settings.admin_alert_recipient_list

    if configured:
        return configured

    emails = db.scalars(
        select(User.email)
        .where(
            User.role == "admin",
            User.is_active.is_(True),
        )
        .order_by(User.id)
    ).all()

    return [email for email in emails if email]


def _deliver_admin_alert(
    recipients: list[str],
    title: str,
    message: str,
    link: str,
) -> None:
    send_admin_alert(recipients, title, message, link)


def dispatch_admin_alert(
    db: Session, notification: AdminNotification
) -> None:
    if (
        not settings.admin_email_alerts_enabled
        or not settings.smtp_configured
    ):
        return

    recipients = admin_alert_recipients(db)

    if not recipients:
        return

    _alert_executor().submit(
        _deliver_admin_alert,
        recipients,
        notification.title,
        notification.message,
        notification.link,
    )


def flush_admin_alerts(timeout: float = 5.0) -> None:
    """Wait for queued alert emails (used by tests and shutdown)."""

    if _executor is not None:
        _executor.submit(lambda: None).result(timeout=timeout)


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
    dispatch_admin_alert(db, notification)
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
