import asyncio
import json
import logging
from concurrent.futures import Future

from fastapi import WebSocket
from sqlalchemy.orm import Session

from ..models.notification import Notification, NotificationType
from ..repositories import notification_repo


logger = logging.getLogger("pawshome.notifications")

_connections: dict[int, tuple[WebSocket, asyncio.AbstractEventLoop]] = {}


def register_ws(
    user_id: int,
    websocket: WebSocket,
    loop: asyncio.AbstractEventLoop,
) -> None:
    _connections[user_id] = (websocket, loop)


def unregister_ws(user_id: int, websocket: WebSocket | None = None) -> None:
    current = _connections.get(user_id)
    if current is None:
        return
    if websocket is not None and current[0] is not websocket:
        return
    _connections.pop(user_id, None)


def serialize(notification: Notification) -> dict:
    notification_type = notification.type
    return {
        "id": notification.id,
        "user_id": notification.user_id,
        "title": notification.title,
        "message": notification.message,
        "type": (
            notification_type.value
            if isinstance(notification_type, NotificationType)
            else notification_type
        ),
        "is_read": notification.is_read,
        "related_pet_id": notification.related_pet_id,
        "created_at": (
            notification.created_at.isoformat() if notification.created_at else None
        ),
    }


async def _deliver(websocket: WebSocket, payload: dict) -> None:
    await websocket.send_text(json.dumps(payload, default=str))


def _log_failure(future: Future) -> None:
    error = future.exception()
    if error is not None:
        logger.info("WebSocket delivery failed: %s", error)


def publish(user_id: int, payload: dict) -> None:
    """Schedule a push on the connection's own event loop.

    HTTP handlers run in a worker thread, so the coroutine cannot be created
    with ``asyncio.ensure_future`` (there is no loop in that thread). The loop
    captured when the socket was accepted is the only safe place to schedule it.
    """
    connection = _connections.get(user_id)
    if connection is None:
        return

    websocket, loop = connection
    if loop.is_closed():
        _connections.pop(user_id, None)
        return

    try:
        future = asyncio.run_coroutine_threadsafe(_deliver(websocket, payload), loop)
    except RuntimeError:
        _connections.pop(user_id, None)
        return

    future.add_done_callback(_log_failure)


def send(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    ntype: NotificationType,
    related_pet_id: int | None = None,
) -> Notification:
    """Persist a notification inside the caller's transaction.

    The caller commits first and then calls :func:`publish`, so a rolled back
    transaction never leaks a phantom event over the socket.
    """
    return notification_repo.create(
        db=db,
        user_id=user_id,
        title=title,
        message=message,
        ntype=ntype,
        related_pet_id=related_pet_id,
    )


def get_user_notifications(db: Session, user_id: int) -> list[Notification]:
    return notification_repo.get_for_user(db, user_id)


def unread_count(db: Session, user_id: int) -> int:
    return notification_repo.count_unread(db, user_id)
