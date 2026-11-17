from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db, transaction
from ..repositories import notification_repo
from ..schemas.notification import NotificationOut, UnreadCount
from ..services import notification_service
from .deps import get_current_user


router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return notification_service.get_user_notifications(db, current_user.id)


@router.get("/unread-count", response_model=UnreadCount)
def unread_count(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return UnreadCount(unread=notification_service.unread_count(db, current_user.id))


@router.post("/read-all", response_model=UnreadCount)
def mark_all_read(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    with transaction(db):
        notification_repo.mark_all_read(db, current_user.id)
    return UnreadCount(unread=0)


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notification = notification_repo.get_by_id_for_user(
        db, notification_id, current_user.id
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")

    with transaction(db):
        return notification_repo.mark_read(db, notification)
