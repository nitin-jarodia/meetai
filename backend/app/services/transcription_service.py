"""Speech-to-text via local OpenAI Whisper + pluggable diarization."""

from __future__ import annotations

import logging
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Sequence

from app.core.config import settings

logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """Raised when Whisper fails or returns unusable output."""


@dataclass(slots=True)
class SegmentData:
    order_index: int
    start_ms: int
    end_ms: int
    text: str
    speaker_label: str = "Speaker 1"
    confidence: float | None = None


@dataclass(slots=True)
class TranscriptionResult:
    text: str
    language: str | None
    duration_ms: int
    segments: list[SegmentData] = field(default_factory=list)


_model_cache: dict[str, Any] = {}
_ffmpeg_path_configured = False


def _ensure_ffmpeg_on_path() -> None:
    """Put an ffmpeg binary on PATH (bundled via imageio-ffmpeg on Windows)."""
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
                "Set it to ffmpeg.exe or its folder, or leave it empty to use the bundled ffmpeg."
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
            f"or set FFMPEG_PATH. Details: {e}"
        ) from e

    resolved = Path(exe).resolve()
    # Whisper spawns "ffmpeg"; imageio-ffmpeg ships a versioned filename on Windows,
    # so we symlink-copy it into a cache dir and prepend that to PATH.
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


def _build_segments(raw_segments: Sequence[dict[str, Any]] | None) -> list[SegmentData]:
    """Convert Whisper's segment dicts into our dataclass, merging trivially short ones."""
    if not raw_segments:
        return []
    segments: list[SegmentData] = []
    for idx, seg in enumerate(raw_segments):
        text = str(seg.get("text") or "").strip()
        if not text:
            continue
        start_s = float(seg.get("start") or 0.0)
        end_s = float(seg.get("end") or start_s)
        if end_s < start_s:
            end_s = start_s
        conf_raw = seg.get("avg_logprob")
        # Whisper returns negative log-probs; map to a 0..1ish confidence.
        confidence: float | None = None
        if isinstance(conf_raw, (int, float)):
            try:
                # exp of log-prob is well-defined; clamp to [0, 1].
                import math

                confidence = float(max(0.0, min(1.0, math.exp(conf_raw))))
            except (ValueError, OverflowError):
                confidence = None
        segments.append(
            SegmentData(
                order_index=idx,
                start_ms=int(start_s * 1000),
                end_ms=int(end_s * 1000),
                text=text,
                confidence=confidence,
            )
        )
    # Re-number order_index in case empty segments were skipped.
    for i, s in enumerate(segments):
        s.order_index = i
    return segments


# ---------------------------------------------------------------------------
# Diarization (pluggable)
# ---------------------------------------------------------------------------


class DiarizationService:
    """Interface for speaker diarization backends."""

    def label_segments(
        self, audio_path: Path, segments: List[SegmentData]
    ) -> List[SegmentData]:
        raise NotImplementedError


class NoOpDiarizer(DiarizationService):
    """Single-speaker labeler — safe default when diarization is disabled."""

    def label_segments(
        self, audio_path: Path, segments: List[SegmentData]
    ) -> List[SegmentData]:
        for s in segments:
            s.speaker_label = "Speaker 1"
        return segments


class PyannoteDiarizer(DiarizationService):
    """
    pyannote.audio-based diarization. Lazy-imported; requires a Hugging Face token.
    Falls back to single-speaker labeling on any error.
    """

    def __init__(self, hf_token: str) -> None:
        self._hf_token = hf_token
        self._pipeline: Any | None = None

    def _load(self) -> Any | None:
        if self._pipeline is not None:
            return self._pipeline
        try:
            from pyannote.audio import Pipeline  # type: ignore

            self._pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=self._hf_token or None,
            )
            return self._pipeline
        except Exception as exc:  # pragma: no cover — depends on optional dep
            logger.warning("pyannote diarization unavailable: %s", exc)
            self._pipeline = None
            return None

    def label_segments(
        self, audio_path: Path, segments: List[SegmentData]
    ) -> List[SegmentData]:
        if not segments:
            return segments
        pipeline = self._load()
        if pipeline is None:
            return NoOpDiarizer().label_segments(audio_path, segments)
        try:
            diarization = pipeline(str(audio_path))
        except Exception as exc:  # pragma: no cover
            logger.warning("pyannote diarization run failed: %s", exc)
            return NoOpDiarizer().label_segments(audio_path, segments)

        # Build (start_s, end_s, speaker) turns
        turns: list[tuple[float, float, str]] = []
        try:
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                turns.append((float(turn.start), float(turn.end), str(speaker)))
        except Exception as exc:  # pragma: no cover
            logger.warning("pyannote turn iteration failed: %s", exc)
            return NoOpDiarizer().label_segments(audio_path, segments)

        # Assign each Whisper segment the speaker with the largest time overlap.
        speaker_index: dict[str, int] = {}
        for seg in segments:
            seg_start = seg.start_ms / 1000.0
            seg_end = seg.end_ms / 1000.0
            best: tuple[float, str] = (0.0, "Speaker 1")
            for t_start, t_end, speaker in turns:
                overlap = max(0.0, min(seg_end, t_end) - max(seg_start, t_start))
                if overlap > best[0]:
                    best = (overlap, speaker)
            raw = best[1]
            if raw not in speaker_index:
                speaker_index[raw] = len(speaker_index) + 1
            seg.speaker_label = f"Speaker {speaker_index[raw]}"
        return segments


_diarizer_singleton: DiarizationService | None = None


def get_diarizer() -> DiarizationService:
    global _diarizer_singleton
    if _diarizer_singleton is not None:
        return _diarizer_singleton
    backend = (settings.diarization_backend or "none").strip().lower()
    if backend == "pyannote":
        _diarizer_singleton = PyannoteDiarizer(settings.huggingface_token)
    else:
        _diarizer_singleton = NoOpDiarizer()
    return _diarizer_singleton


# ---------------------------------------------------------------------------
# Public transcription API
# ---------------------------------------------------------------------------


def transcribe_audio(file_path: str | Path) -> TranscriptionResult:
    """
    Transcribe an audio file with local Whisper, returning segments + language.

    Segment timestamps use Whisper's built-in VAD. Diarization is applied when
    configured. The result's `.text` is the full concatenated text for
    backwards compatibility.
    """
    path = Path(file_path)
    if not path.is_file():
        raise TranscriptionError(f"Audio file not found: {path}")

    _ensure_ffmpeg_on_path()

    try:
        import whisper  # noqa: F401
    except ImportError as e:
        raise TranscriptionError(
            "openai-whisper is not installed. Install with: pip install openai-whisper"
        ) from e

    try:
        model = _load_whisper_model(settings.whisper_model)
        result = model.transcribe(str(path), verbose=False)
    except Exception as e:
        raise TranscriptionError(f"Transcription failed: {e}") from e

    text = str(result.get("text") or "").strip()
    if not text:
        raise TranscriptionError("Transcription produced empty text")

    language = result.get("language")
    segments = _build_segments(result.get("segments"))

    try:
        get_diarizer().label_segments(path, segments)
    except Exception as exc:  # pragma: no cover — safety net
        logger.warning("Diarization failed, falling back to single speaker: %s", exc)
        NoOpDiarizer().label_segments(path, segments)

    duration_ms = 0
    if segments:
        duration_ms = max(s.end_ms for s in segments)

    return TranscriptionResult(
        text=text,
        language=str(language) if language else None,
        duration_ms=duration_ms,
        segments=segments,
    )


def transcribe_chunk(audio_bytes: bytes, model_name: str | None = None) -> str:
    """Transcribe a short live-recording chunk and return plain text."""
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

    def transcribe_file(self, file_path: str | Path) -> TranscriptionResult:
        return transcribe_audio(file_path)
