from datetime import datetime

from pydantic import BaseModel, ConfigDict

from ..models.notification import NotificationType


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    message: str
    type: NotificationType
    is_read: bool
    related_pet_id: int | None = None
    created_at: datetime


class UnreadCount(BaseModel):
    unread: int
