from __future__ import annotations

import asyncio
import types
from unittest.mock import AsyncMock, Mock, patch

import app.services.transcription_service as transcription_service
from app.services.transcription_service import transcribe_chunk
from app.websocket.manager import ConnectionManager


def test_transcribe_chunk_with_mocked_whisper() -> None:
    transcription_service._model_cache.clear()
    mock_model = Mock()
    mock_model.transcribe.return_value = {"text": "hello world"}
    mock_whisper = types.SimpleNamespace(load_model=Mock(return_value=mock_model))

    with patch("app.services.transcription_service._ensure_ffmpeg_on_path"), patch.dict(
        "sys.modules", {"whisper": mock_whisper}
    ):
        assert transcribe_chunk(b"fake audio") == "hello world"


def test_transcribe_chunk_with_empty_bytes() -> None:
    assert transcribe_chunk(b"") == ""


def test_broadcast_to_meeting_sends_to_all_connections() -> None:
    manager = ConnectionManager()
    socket_one = Mock()
    socket_one.send_json = AsyncMock()
    socket_two = Mock()
    socket_two.send_json = AsyncMock()

    manager._connections["room-1"] = {socket_one, socket_two}

    payload = {"type": "test"}
    asyncio.run(manager.broadcast_to_meeting("room-1", payload))

    socket_one.send_json.assert_awaited_once_with(payload)
    socket_two.send_json.assert_awaited_once_with(payload)
