"""Simple room-based WebSocket registry (per meeting_id)."""

import uuid
from typing import Dict, Set

from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    def __init__(self) -> None:
        # meeting_id -> set of websockets
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._rooms = self._connections

    async def connect(self, meeting_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        key = str(meeting_id)
        if key not in self._connections:
            self._connections[key] = set()
        self._connections[key].add(websocket)

    def disconnect(self, meeting_id: uuid.UUID, websocket: WebSocket) -> None:
        key = str(meeting_id)
        if key in self._connections:
            self._connections[key].discard(websocket)
            if not self._connections[key]:
                del self._connections[key]

    @property
    def room_count(self) -> int:
        return len(self._connections)

    async def broadcast_to_meeting(self, meeting_id: str, data: dict) -> None:
        sockets = list(self._connections.get(meeting_id, set()))
        for websocket in sockets:
            try:
                await websocket.send_json(data)
            except WebSocketDisconnect:
                pass

    async def broadcast_json(self, meeting_id: uuid.UUID, payload: dict) -> None:
        await self.broadcast_to_meeting(str(meeting_id), payload)


manager = ConnectionManager()
