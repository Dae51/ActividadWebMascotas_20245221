import asyncio
import json

from fastapi import WebSocket
from sqlalchemy.orm import Session

from ..models.notification import Notification
from ..repositories import notification_repo


_connections: dict[int, WebSocket] = {}



def register_ws(user_id: int, websocket: WebSocket) -> None:
    _connections[user_id] = websocket



def unregister_ws(user_id: int) -> None:
    _connections.pop(user_id, None)



async def push(user_id: int, payload_dict: dict) -> None:
    websocket = _connections.get(user_id)
    if websocket is None:
        return

    await websocket.send_text(json.dumps(payload_dict, default=str))



def send(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    ntype,
    related_pet_id: int | None = None,
) -> Notification:
    notification = notification_repo.create(
        db=db,
        user_id=user_id,
        title=title,
        message=message,
        ntype=ntype,
        related_pet_id=related_pet_id,
    )

    payload = {
        "id": notification.id,
        "user_id": notification.user_id,
        "title": notification.title,
        "message": notification.message,
        "type": notification.type.value if hasattr(notification.type, "value") else notification.type,
        "is_read": notification.is_read,
        "related_pet_id": notification.related_pet_id,
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
    }

    try:
        asyncio.ensure_future(push(user_id, payload))
    except RuntimeError:
        pass

    return notification



def get_user_notifications(db: Session, user_id: int) -> list[Notification]:
    return notification_repo.get_for_user(db, user_id)
