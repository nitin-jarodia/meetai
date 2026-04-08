import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import decode_token
from app.websocket.manager import manager

router = APIRouter()


@router.websocket("/ws/meetings/{meeting_id}")
async def meeting_socket(websocket: WebSocket, meeting_id: uuid.UUID):
    token = websocket.query_params.get("token")
    user_id: str | None = None
    if token:
        user_id = decode_token(token)

    await manager.connect(meeting_id, websocket)
    try:
        await websocket.send_json(
            {
                "type": "connected",
                "meeting_id": str(meeting_id),
                "authenticated": user_id is not None,
            }
        )
        while True:
            data = await websocket.receive_text()
            # Echo for scaffolding — replace with events (chat, presence, signals).
            await websocket.send_json({"type": "echo", "payload": data})
    except WebSocketDisconnect:
        manager.disconnect(meeting_id, websocket)
