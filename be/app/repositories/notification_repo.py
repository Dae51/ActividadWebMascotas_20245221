from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..models.notification import Notification



def create(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    ntype,
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
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    db.refresh(notification)
    return notification



def get_for_user(db: Session, user_id: int) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(desc(Notification.created_at))
    )
    return list(db.scalars(stmt).all())



def mark_read(db: Session, notification_id: int, user_id: int) -> Notification | None:
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    )
    notification = db.scalar(stmt)
    if notification is None:
        return None

    notification.is_read = True
    db.add(notification)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    db.refresh(notification)
    return notification
