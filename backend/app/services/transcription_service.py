"""Speech-to-text via local OpenAI Whisper."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.config import settings


class TranscriptionError(Exception):
    """Raised when Whisper fails or returns unusable output."""


_model_cache: dict[str, Any] = {}


def _load_whisper_model(model_name: str) -> Any:
    if model_name not in _model_cache:
        import whisper

        _model_cache[model_name] = whisper.load_model(model_name)
    return _model_cache[model_name]


def transcribe_audio(file_path: str | Path) -> str:
    """
    Transcribe an audio file to plain text using local Whisper.

    Model name comes from settings.whisper_model (e.g. tiny, base).
    """
    path = Path(file_path)
    if not path.is_file():
        raise TranscriptionError(f"Audio file not found: {path}")

    try:
        import whisper  # noqa: F401 — optional dependency
    except ImportError as e:
        raise TranscriptionError(
            "openai-whisper is not installed. Install with: pip install openai-whisper"
        ) from e

    try:
        model = _load_whisper_model(settings.whisper_model)
        result = model.transcribe(str(path))
        text = (result.get("text") or "").strip()
        if not text:
            raise TranscriptionError("Transcription produced empty text")
        return text
    except TranscriptionError:
        raise
    except Exception as e:
        raise TranscriptionError(f"Transcription failed: {e}") from e


class TranscriptionService:
    """Thin wrapper for tests and future streaming/chunking."""

    def transcribe_file(self, file_path: str | Path) -> str:
        return transcribe_audio(file_path)
