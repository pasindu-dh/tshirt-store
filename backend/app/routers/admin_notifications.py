from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.schemas.notification import (
    AdminNotificationOut,
    NotificationMarkAllOut,
    NotificationUnreadCountOut,
)
from app.services import notifications

router = APIRouter(
    prefix="/admin/notifications",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=list[AdminNotificationOut])
def list_notifications(
    response: Response,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    items, total = notifications.list_notifications(
        db,
        page=page,
        limit=limit,
        unread_only=unread_only,
    )
    response.headers["X-Total-Count"] = str(total)
    return items


@router.get(
    "/unread-count",
    response_model=NotificationUnreadCountOut,
)
def get_unread_count(db: Session = Depends(get_db)):
    return NotificationUnreadCountOut(
        count=notifications.unread_count(db)
    )


@router.post(
    "/read-all",
    response_model=NotificationMarkAllOut,
)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
):
    return NotificationMarkAllOut(
        updated=notifications.mark_all_read(db)
    )


@router.patch(
    "/{notification_id}/read",
    response_model=AdminNotificationOut,
)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
):
    notification = notifications.mark_read(
        db, notification_id
    )

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    return notification
