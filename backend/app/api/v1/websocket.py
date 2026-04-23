import asyncio
import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.database import AsyncSessionLocal
from app.core.security import decode_token
from app.repositories.user_repository import UserRepository
from app.services.ai_service import AIService
from app.services.live_summary import LiveSummaryEngine
from app.services.transcription_service import transcribe_chunk
from app.websocket.manager import manager

router = APIRouter()


@router.websocket("/ws/meetings/{meeting_id}")
async def meeting_socket(websocket: WebSocket, meeting_id: uuid.UUID):
    token = websocket.query_params.get("token")
    user_sub: str | None = decode_token(token) if token else None
    if not user_sub:
        await websocket.close(code=1008)
        return

    try:
        user_uuid = uuid.UUID(user_sub)
    except ValueError:
        await websocket.close(code=1008)
        return

    async with AsyncSessionLocal() as session:
        user = await UserRepository(session).get_by_id(user_uuid)
    if not user:
        await websocket.close(code=1008)
        return

    await manager.connect(meeting_id, websocket)

    async def emit_to_room(payload: dict) -> None:
        await manager.broadcast_to_meeting(str(meeting_id), payload)

    summary_engine = LiveSummaryEngine(AIService(), emit_to_room)

    try:
        await websocket.send_json(
            {
                "type": "connected",
                "meeting_id": str(meeting_id),
                "authenticated": True,
            }
        )
        while True:
            message = await websocket.receive()
            message_type = message.get("type")
            if message_type == "websocket.disconnect":
                raise WebSocketDisconnect()

            payload_bytes = message.get("bytes")
            payload_text = message.get("text")

            if payload_bytes is not None:
                text = await asyncio.to_thread(transcribe_chunk, payload_bytes)
                if text:
                    await manager.broadcast_to_meeting(
                        str(meeting_id),
                        {
                            "type": "transcript_delta",
                            "text": text,
                            "user_id": str(user.id),
                        },
                    )
                    summary_engine.ingest(text)
                    # Fire-and-forget: the engine debounces internally so this
                    # is safe to call on every incoming chunk.
                    asyncio.create_task(summary_engine.maybe_emit())
                continue

            if payload_text is None:
                continue

            if payload_text == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            if payload_text == "stop":
                break

            try:
                body = json.loads(payload_text)
            except json.JSONDecodeError:
                continue

            msg_type = body.get("type")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "stop":
                break
            elif msg_type == "transcript_delta":
                text = str(body.get("text") or "").strip()
                if text:
                    summary_engine.ingest(text)
                    asyncio.create_task(summary_engine.maybe_emit())
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(meeting_id, websocket)
