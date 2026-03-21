from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError

from ..services import notification_service
from ..services.auth_service import decode_token


router = APIRouter(tags=["ws"])


@router.websocket("/ws/notifications")
async def notifications_ws(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return

    try:
        token_data = decode_token(token)
    except JWTError:
        await websocket.close(code=1008)
        return

    user_id = token_data.user_id
    if user_id is None:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    notification_service.register_ws(user_id, websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_service.unregister_ws(user_id)
