"""Simple room-based WebSocket registry (per meeting_id)."""

import uuid
from typing import Dict, Set

from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    def __init__(self) -> None:
        # meeting_id -> set of websockets
        self._rooms: Dict[str, Set[WebSocket]] = {}

    async def connect(self, meeting_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        key = str(meeting_id)
        if key not in self._rooms:
            self._rooms[key] = set()
        self._rooms[key].add(websocket)

    def disconnect(self, meeting_id: uuid.UUID, websocket: WebSocket) -> None:
        key = str(meeting_id)
        if key in self._rooms:
            self._rooms[key].discard(websocket)
            if not self._rooms[key]:
                del self._rooms[key]

    @property
    def room_count(self) -> int:
        return len(self._rooms)

    async def broadcast_json(self, meeting_id: uuid.UUID, payload: dict) -> None:
        key = str(meeting_id)
        sockets = list(self._rooms.get(key, set()))
        for websocket in sockets:
            try:
                await websocket.send_json(payload)
            except WebSocketDisconnect:
                self.disconnect(meeting_id, websocket)
            except RuntimeError:
                self.disconnect(meeting_id, websocket)


manager = ConnectionManager()
