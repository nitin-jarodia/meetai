from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.ai_service import AIService, SummaryGenerationError, get_ai_service
    from app.services.meeting_service import MeetingService
    from app.services.transcript_service import TranscriptService
    from app.services.transcription_service import (
        TranscriptionError,
        TranscriptionService,
    )


def __getattr__(name: str):
    if name in {"AIService", "SummaryGenerationError", "get_ai_service"}:
        from app.services.ai_service import AIService, SummaryGenerationError, get_ai_service

        return {
            "AIService": AIService,
            "SummaryGenerationError": SummaryGenerationError,
            "get_ai_service": get_ai_service,
        }[name]
    if name == "MeetingService":
        from app.services.meeting_service import MeetingService

        return MeetingService
    if name == "TranscriptService":
        from app.services.transcript_service import TranscriptService

        return TranscriptService
    if name in {"TranscriptionError", "TranscriptionService"}:
        from app.services.transcription_service import (
            TranscriptionError,
            TranscriptionService,
        )

        return {
            "TranscriptionError": TranscriptionError,
            "TranscriptionService": TranscriptionService,
        }[name]
    raise AttributeError(name)

__all__ = [
    "AIService",
    "SummaryGenerationError",
    "get_ai_service",
    "MeetingService",
    "TranscriptService",
    "TranscriptionError",
    "TranscriptionService",
]
