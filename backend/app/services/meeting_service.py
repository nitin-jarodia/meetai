"""Meeting use cases."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meeting import Meeting
from app.models.participant import Participant
from app.models.transcript import Transcript
from app.models.user import User
from app.repositories.meeting_repository import MeetingRepository
from app.schemas.meeting import MeetingCreate, MeetingDetail, MeetingOut, ParticipantBrief, TranscriptBrief
from app.schemas.user import UserOut
from app.services.ai_service import AIService
from app.services.transcription_service import transcribe_audio, TranscriptionError


class MeetingNotFoundError(Exception):
    """Raised when no meeting exists for the given id."""


class MeetingAccessDeniedError(Exception):
    """Raised when the user is not the host or a participant."""


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

    async def process_audio_upload(
        self,
        meeting_id: uuid.UUID,
        user: User,
        saved_file_path: Path,
        ai: AIService,
    ) -> tuple[str, str]:
        """
        Transcribe audio, summarize with Groq, persist Transcript, return (transcript, summary).

        Raises MeetingNotFoundError, MeetingAccessDeniedError, TranscriptionError, SummaryGenerationError.
        """
        meeting = await self._get_meeting_for_user(meeting_id, user)
        transcript_text = await asyncio.to_thread(transcribe_audio, str(saved_file_path))
        summary = await asyncio.to_thread(ai.generate_summary, transcript_text)
        now = datetime.now(timezone.utc)
        await self.meetings.add_transcript(
            Transcript(
                meeting_id=meeting.id,
                content=transcript_text,
                segment_index=None,
                created_at=now,
            )
        )
        return transcript_text, summary
