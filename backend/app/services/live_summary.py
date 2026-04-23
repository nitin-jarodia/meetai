"""Rolling live summary generator for in-progress meetings.

Aggregates incoming `transcript_delta` chunks per WebSocket and periodically
asks Groq for a short summary + open questions. Falls back to a local extractive
summary when Groq is unavailable, so the UI still shows something.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from app.core.config import settings
from app.services.ai_service import (
    AIService,
    SummaryGenerationError,
    _top_sentences,  # type: ignore  # reuse extractive helper
)

logger = logging.getLogger(__name__)

_LIVE_SUMMARY_PROMPT = (
    "You are assisting a live meeting. The user will provide the running "
    "transcript so far. Return STRICT JSON: "
    '{"summary":"1-3 sentences","open_questions":["..."],"next_steps":["..."]}. '
    "Keep each field grounded in the transcript. Do not add code fences."
)


@dataclass(slots=True)
class LiveSummaryState:
    buffer: list[str] = field(default_factory=list)
    char_count: int = 0
    last_summary_at: float = 0.0
    last_summary: str = ""
    last_length_at_emit: int = 0
    task: asyncio.Task[None] | None = None


class LiveSummaryEngine:
    """One instance per WS connection; cheap, in-process, and cancellable."""

    def __init__(
        self,
        ai: AIService,
        emit: Callable[[dict], Awaitable[None]],
    ) -> None:
        self._ai = ai
        self._emit = emit
        self._state = LiveSummaryState()
        self._lock = asyncio.Lock()

    def ingest(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        self._state.buffer.append(text)
        self._state.char_count += len(text) + 1

    async def maybe_emit(self) -> None:
        now = time.monotonic()
        since = now - (self._state.last_summary_at or 0.0)
        new_chars = self._state.char_count - self._state.last_length_at_emit
        if since < settings.live_summary_interval_seconds:
            return
        if new_chars < settings.live_summary_min_new_chars:
            return
        if self._lock.locked():
            return

        async with self._lock:
            full_text = " ".join(self._state.buffer).strip()
            if not full_text:
                return
            try:
                summary = await asyncio.wait_for(
                    asyncio.to_thread(self._generate, full_text),
                    timeout=12.0,
                )
            except (asyncio.TimeoutError, Exception) as exc:
                logger.debug("Live summary fallback: %s", exc)
                summary = _local_rolling_summary(full_text)

            self._state.last_summary_at = now
            self._state.last_length_at_emit = self._state.char_count
            self._state.last_summary = summary
            await self._emit(
                {
                    "type": "live_summary_updated",
                    "summary": summary,
                    "char_count": self._state.char_count,
                }
            )

    def _generate(self, full_text: str) -> str:
        if not settings.groq_api_key:
            return _local_rolling_summary(full_text)
        try:
            from groq import Groq  # local import keeps test startup cheap

            client = Groq(api_key=settings.groq_api_key)
            chat = client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {"role": "system", "content": _LIVE_SUMMARY_PROMPT},
                    {"role": "user", "content": full_text[-8000:]},
                ],
                temperature=0.2,
                max_tokens=400,
            )
            content = (chat.choices[0].message.content or "").strip()
            if not content:
                raise SummaryGenerationError("Empty live summary")
            return content
        except Exception as exc:  # pragma: no cover
            logger.debug("Live summary Groq failed: %s", exc)
            return _local_rolling_summary(full_text)


def _local_rolling_summary(text: str) -> str:
    """Extractive fallback that never blocks the event loop."""
    highlights = _top_sentences(text, limit=3)
    if not highlights:
        return ""
    bullets = "\n".join(f"• {s}" for s in highlights)
    return (
        '{"summary":"'
        + highlights[0].replace('"', "'")
        + '","open_questions":[],"next_steps":[],"bullets":"'
        + bullets.replace('"', "'").replace("\n", " ")
        + '"}'
    )
