import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError

from ..services import notification_service
from ..services.auth_service import decode_ws_ticket


router = APIRouter(tags=["ws"])

HANDSHAKE_TIMEOUT_SECONDS = 10


async def _read_ticket(websocket: WebSocket) -> str | None:
    try:
        raw = await asyncio.wait_for(
            websocket.receive_text(),
            timeout=HANDSHAKE_TIMEOUT_SECONDS,
        )
    except (TimeoutError, WebSocketDisconnect):
        return None

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None

    ticket = payload.get("ticket")
    return ticket if isinstance(ticket, str) else None


@router.websocket("/ws/notifications")
async def notifications_ws(websocket: WebSocket):
    await websocket.accept()

    ticket = await _read_ticket(websocket)
    if not ticket:
        await websocket.close(code=1008)
        return

    try:
        token_data = decode_ws_ticket(ticket)
    except JWTError:
        await websocket.close(code=1008)
        return

    user_id = token_data.user_id
    if user_id is None:
        await websocket.close(code=1008)
        return

    loop = asyncio.get_running_loop()
    notification_service.register_ws(user_id, websocket, loop)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_service.unregister_ws(user_id, websocket)
