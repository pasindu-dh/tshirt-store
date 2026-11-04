from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AdminNotificationOut(BaseModel):
    id: int
    notification_type: str
    title: str
    message: str
    link: str
    is_read: bool
    read_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationUnreadCountOut(BaseModel):
    count: int


class NotificationMarkAllOut(BaseModel):
    updated: int
