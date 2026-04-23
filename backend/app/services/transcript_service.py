"""Transcript editing and regeneration use cases."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transcript import Transcript
from app.models.user import User
from app.repositories.meeting_repository import MeetingRepository
from app.repositories.transcript_repository import TranscriptRepository
from app.services.action_item_service import sync_ai_action_items
from app.services.ai_service import AIService, SummaryGenerationError
from app.services.search_service import SearchService


class TranscriptNotFoundError(Exception):
    """Raised when the transcript does not exist."""


class TranscriptAccessDeniedError(Exception):
    """Raised when the user cannot access the transcript's meeting."""


@dataclass(slots=True)
class TranscriptUpdateResult:
    message: str


class TranscriptService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.transcripts = TranscriptRepository(session)
        self.meetings = MeetingRepository(session)

    async def _get_transcript_for_user(
        self, transcript_id: uuid.UUID, user: User
    ) -> Transcript:
        transcript = await self.transcripts.get_by_id(transcript_id)
        if not transcript:
            raise TranscriptNotFoundError()

        meeting = await self.meetings.get_by_id(transcript.meeting_id)
        if not meeting:
            raise TranscriptNotFoundError()
        if meeting.host_id == user.id:
            return transcript
        if await self.meetings.get_participant(meeting.id, user.id):
            return transcript
        raise TranscriptAccessDeniedError()

    async def get_transcript_with_segments(
        self, transcript_id: uuid.UUID, user: User
    ) -> Transcript:
        transcript = await self._get_transcript_for_user(transcript_id, user)
        # Force-load segments eagerly.
        hydrated = await self.transcripts.get_with_segments(transcript.id)
        return hydrated or transcript

    @staticmethod
    def _get_cleaned_source(transcript: Transcript) -> str:
        return (
            (transcript.cleaned_transcript or "").strip()
            or (transcript.transcript_text or "").strip()
            or (transcript.content or "").strip()
        )

    async def update_cleaned_transcript(
        self, transcript_id: uuid.UUID, user: User, cleaned_transcript: str
    ) -> TranscriptUpdateResult:
        transcript = await self._get_transcript_for_user(transcript_id, user)
        transcript.cleaned_transcript = cleaned_transcript.strip()
        await self.transcripts.save(transcript)
        return TranscriptUpdateResult(message="Transcript updated successfully")

    async def regenerate_transcript_summary(
        self, transcript_id: uuid.UUID, user: User, ai: AIService
    ) -> Transcript:
        transcript = await self._get_transcript_for_user(transcript_id, user)
        cleaned_source = self._get_cleaned_source(transcript)
        if not cleaned_source:
            raise TranscriptNotFoundError()

        transcript.cleaned_transcript = cleaned_source
        try:
            analysis = await asyncio.to_thread(ai.generate_analysis, cleaned_source)
        except SummaryGenerationError:
            analysis = ai.fallback_analysis(cleaned_source)

        transcript.summary = analysis.summary
        transcript.key_points = analysis.key_points
        meeting = await self.meetings.get_by_id(transcript.meeting_id)
        if not meeting:
            raise TranscriptNotFoundError()
        transcript.action_items = [item.model_dump() for item in analysis.action_items]
        await sync_ai_action_items(self.session, meeting, transcript, analysis.action_items)
        await SearchService(self.session).index_transcript(meeting, transcript)
        await self.transcripts.save(transcript)
        return transcript
