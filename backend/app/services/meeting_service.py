"""Meeting use cases."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meeting import Meeting
from app.models.participant import Participant
from app.models.transcript import Transcript
from app.models.user import User
from app.repositories.meeting_repository import MeetingRepository
from app.schemas.meeting import (
    MeetingCreate,
    MeetingDetail,
    MeetingOut,
    ParticipantBrief,
    TranscriptBrief,
)
from app.schemas.user import UserOut
from app.services.ai_service import (
    AIService,
    MeetingAnalysis,
    QuestionAnsweringError,
    SummaryGenerationError,
)
from app.services.transcription_service import transcribe_audio, TranscriptionError


class MeetingNotFoundError(Exception):
    """Raised when no meeting exists for the given id."""


class MeetingAccessDeniedError(Exception):
    """Raised when the user is not the host or a participant."""


class TranscriptNotFoundError(Exception):
    """Raised when no transcript exists for the meeting."""


@dataclass(slots=True)
class ProcessedAudioUpload:
    transcript: str
    summary: str
    key_points: list[str]
    action_items: list[dict[str, str | None]]


@dataclass(slots=True)
class MeetingAnswer:
    answer: str


class MeetingService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.meetings = MeetingRepository(session)

    async def create_meeting(self, host: User, data: MeetingCreate) -> MeetingOut:
        now = datetime.now(timezone.utc)
        meeting = Meeting(
            title=data.title,
            description=data.description,
            host_id=host.id,
            created_at=now,
        )
        await self.meetings.create(meeting)
        # Host is implicitly a participant for UX
        await self.meetings.add_participant(
            Participant(
                meeting_id=meeting.id,
                user_id=host.id,
                role="host",
                joined_at=now,
            )
        )
        return MeetingOut.model_validate(meeting)

    async def join_meeting(self, meeting_id: uuid.UUID, user: User) -> MeetingOut:
        meeting = await self.meetings.get_by_id(meeting_id)
        if not meeting:
            raise ValueError("Meeting not found")
        existing = await self.meetings.get_participant(meeting_id, user.id)
        if existing:
            return MeetingOut.model_validate(meeting)
        await self.meetings.add_participant(
            Participant(
                meeting_id=meeting.id,
                user_id=user.id,
                role="member",
                joined_at=datetime.now(timezone.utc),
            )
        )
        meeting = await self.meetings.get_by_id(meeting_id)
        assert meeting is not None
        return MeetingOut.model_validate(meeting)

    async def get_meeting_detail(self, meeting_id: uuid.UUID) -> MeetingDetail | None:
        meeting = await self.meetings.get_by_id(meeting_id)
        if not meeting:
            return None
        host_out = UserOut.model_validate(meeting.host)
        parts = []
        for p in meeting.participants:
            parts.append(
                ParticipantBrief(
                    user_id=p.user_id,
                    role=p.role,
                    joined_at=p.joined_at,
                    user=UserOut.model_validate(p.user),
                )
            )
        transcripts = [
            TranscriptBrief.model_validate(t) for t in meeting.transcripts
        ]
        return MeetingDetail(
            id=meeting.id,
            title=meeting.title,
            description=meeting.description,
            host_id=meeting.host_id,
            created_at=meeting.created_at,
            host=host_out,
            participants=parts,
            transcripts=transcripts,
        )

    async def _get_meeting_for_user(self, meeting_id: uuid.UUID, user: User) -> Meeting:
        meeting = await self.meetings.get_by_id(meeting_id)
        if not meeting:
            raise MeetingNotFoundError()
        if meeting.host_id == user.id:
            return meeting
        if await self.meetings.get_participant(meeting_id, user.id):
            return meeting
        raise MeetingAccessDeniedError()

    async def _analyze_transcript(
        self, transcript_text: str, ai: AIService
    ) -> MeetingAnalysis:
        try:
            return await asyncio.to_thread(ai.generate_analysis, transcript_text)
        except SummaryGenerationError:
            return ai.fallback_analysis(transcript_text)

    @staticmethod
    def _select_transcript_source(transcript: Transcript) -> str:
        return (
            (transcript.cleaned_transcript or "").strip()
            or (transcript.transcript_text or "").strip()
            or (transcript.content or "").strip()
        )

    async def process_audio_upload(
        self,
        meeting_id: uuid.UUID,
        user: User,
        saved_file_path: Path,
        ai: AIService,
    ) -> ProcessedAudioUpload:
        """
        Transcribe audio, generate structured analysis, persist Transcript, and return
        the structured API payload.

        Raises MeetingNotFoundError, MeetingAccessDeniedError, TranscriptionError.
        """
        meeting = await self._get_meeting_for_user(meeting_id, user)
        transcript_text = await asyncio.to_thread(transcribe_audio, str(saved_file_path))
        analysis = await self._analyze_transcript(transcript_text, ai)
        action_items = [item.model_dump() for item in analysis.action_items]
        now = datetime.now(timezone.utc)
        await self.meetings.add_transcript(
            Transcript(
                meeting_id=meeting.id,
                content=transcript_text,
                transcript_text=transcript_text,
                cleaned_transcript=transcript_text,
                summary=analysis.summary,
                key_points=analysis.key_points,
                action_items=action_items,
                segment_index=None,
                created_at=now,
            )
        )
        return ProcessedAudioUpload(
            transcript=transcript_text,
            summary=analysis.summary,
            key_points=analysis.key_points,
            action_items=action_items,
        )

    async def ask_meeting_question(
        self,
        meeting_id: uuid.UUID,
        user: User,
        question: str,
        ai: AIService,
    ) -> MeetingAnswer:
        meeting = await self._get_meeting_for_user(meeting_id, user)
        transcript = await self.meetings.get_latest_transcript(meeting.id)
        if not transcript:
            raise TranscriptNotFoundError()

        transcript_source = self._select_transcript_source(transcript)
        if not transcript_source:
            raise TranscriptNotFoundError()

        try:
            answer = await asyncio.to_thread(
                ai.answer_question,
                transcript_source,
                question.strip(),
            )
        except QuestionAnsweringError:
            answer = ai.fallback_answer()

        return MeetingAnswer(answer=answer)
