"""Speech-to-text via local OpenAI Whisper."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from app.core.config import settings


class TranscriptionError(Exception):
    """Raised when Whisper fails or returns unusable output."""


_model_cache: dict[str, Any] = {}
_ffmpeg_path_configured = False


def _ensure_ffmpeg_on_path() -> None:
    """
    Whisper decodes audio by spawning `ffmpeg`. On Windows, a missing ffmpeg causes
    WinError 2 ("The system cannot find the file specified"). Prefer a bundled
    binary from imageio-ffmpeg unless FFMPEG_PATH points at ffmpeg or its folder.
    """
    global _ffmpeg_path_configured
    if _ffmpeg_path_configured:
        return

    raw = (settings.ffmpeg_path or "").strip()
    if raw:
        p = Path(raw)
        if p.is_file():
            bin_dir = str(p.resolve().parent)
        elif p.is_dir():
            bin_dir = str(p.resolve())
        else:
            raise TranscriptionError(
                f"FFMPEG_PATH is set but not found: {raw}. "
                "Set it to ffmpeg.exe or the folder that contains it, or leave it empty to use the bundled ffmpeg."
            )
        os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
        _ffmpeg_path_configured = True
        return

    try:
        import imageio_ffmpeg

        exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        raise TranscriptionError(
            "FFmpeg is required for Whisper to decode audio. Install imageio-ffmpeg "
            "(included in requirements) or install FFmpeg and add it to PATH, "
            f"or set FFMPEG_PATH. Details: {e}"
        ) from e

    resolved = Path(exe).resolve()
    # Whisper's subprocess uses the command name "ffmpeg". On Windows, imageio-ffmpeg
    # ships a versioned filename (e.g. ffmpeg-win-x86_64-v7.1.exe), so PATH alone
    # does not help — we copy it to ffmpeg.exe in a small cache dir and prepend that.
    if sys.platform == "win32" and resolved.name.lower() != "ffmpeg.exe":
        cache_dir = Path(__file__).resolve().parents[2] / ".cache" / "ffmpeg"
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise TranscriptionError(
                f"Could not create ffmpeg cache directory {cache_dir}: {e}"
            ) from e
        shim = cache_dir / "ffmpeg.exe"
        try:
            if not shim.is_file():
                shutil.copy2(resolved, shim)
        except OSError as e:
            raise TranscriptionError(
                f"Could not copy bundled ffmpeg to {shim}: {e}"
            ) from e
        bin_dir = str(cache_dir)
    else:
        bin_dir = str(resolved.parent)

    os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
    _ffmpeg_path_configured = True


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

    _ensure_ffmpeg_on_path()

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


def transcribe_chunk(audio_bytes: bytes, model_name: str | None = None) -> str:
    if not audio_bytes:
        return ""

    _ensure_ffmpeg_on_path()

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_file.write(audio_bytes)
            temp_path = Path(temp_file.name)

        model = _load_whisper_model(model_name or settings.whisper_model)
        result = model.transcribe(str(temp_path))
        return str((result.get("text") or "")).strip()
    except Exception:
        return ""
    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


class TranscriptionService:
    """Thin wrapper for tests and future streaming/chunking."""

    def transcribe_file(self, file_path: str | Path) -> str:
        return transcribe_audio(file_path)
