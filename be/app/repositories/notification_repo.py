from sqlalchemy import desc, func, select, update
from sqlalchemy.orm import Session

from ..models.notification import Notification, NotificationType


def create(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    ntype: NotificationType,
    related_pet_id: int | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=ntype,
        related_pet_id=related_pet_id,
    )
    db.add(notification)
    db.flush()
    db.refresh(notification)
    return notification


def get_for_user(db: Session, user_id: int, limit: int = 100) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(desc(Notification.created_at), desc(Notification.id))
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def get_by_id_for_user(
    db: Session,
    notification_id: int,
    user_id: int,
) -> Notification | None:
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    )
    return db.scalar(stmt)


def count_unread(db: Session, user_id: int) -> int:
    stmt = select(func.count(Notification.id)).where(
        Notification.user_id == user_id,
        Notification.is_read.is_(False),
    )
    return int(db.scalar(stmt) or 0)


def mark_read(db: Session, notification: Notification) -> Notification:
    notification.is_read = True
    db.add(notification)
    db.flush()
    db.refresh(notification)
    return notification


def mark_all_read(db: Session, user_id: int) -> int:
    stmt = (
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    result = db.execute(stmt)
    db.flush()
    return int(result.rowcount or 0)
