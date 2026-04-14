import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.meeting import Meeting
from app.models.meeting_action_item import MeetingActionItem
from app.models.meeting_qa import MeetingQAEntry
from app.models.participant import Participant
from app.models.processing_job import MeetingProcessingJob
from app.models.transcript import Transcript


class MeetingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _detail_options(self):
        return (
            selectinload(Meeting.host),
            selectinload(Meeting.participants).selectinload(Participant.user),
            selectinload(Meeting.transcripts),
            selectinload(Meeting.qa_entries).selectinload(MeetingQAEntry.user),
            selectinload(Meeting.action_items).selectinload(
                MeetingActionItem.assigned_user
            ),
            selectinload(Meeting.processing_jobs).selectinload(
                MeetingProcessingJob.created_by
            ),
        )

    async def get_by_id(self, meeting_id: uuid.UUID) -> Meeting | None:
        result = await self.session.execute(
            select(Meeting)
            .where(Meeting.id == meeting_id)
            .options(*self._detail_options())
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: uuid.UUID, query: str | None = None, limit: int = 50
    ) -> list[Meeting]:
        stmt = (
            select(Meeting)
            .join(Participant, Participant.meeting_id == Meeting.id)
            .where(Participant.user_id == user_id)
            .options(*self._detail_options())
            .order_by(Meeting.created_at.desc())
            .limit(limit)
        )
        trimmed = (query or "").strip()
        if trimmed:
            like = f"%{trimmed}%"
            stmt = stmt.where(
                or_(
                    Meeting.title.ilike(like),
                    Meeting.description.ilike(like),
                )
            )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def create(self, meeting: Meeting) -> Meeting:
        self.session.add(meeting)
        await self.session.flush()
        await self.session.refresh(meeting)
        return meeting

    async def add_participant(self, participant: Participant) -> Participant:
        self.session.add(participant)
        await self.session.flush()
        await self.session.refresh(participant)
        return participant

    async def get_participant(
        self, meeting_id: uuid.UUID, user_id: uuid.UUID
    ) -> Participant | None:
        result = await self.session.execute(
            select(Participant).where(
                Participant.meeting_id == meeting_id,
                Participant.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def add_transcript(self, transcript: Transcript) -> Transcript:
        self.session.add(transcript)
        await self.session.flush()
        await self.session.refresh(transcript)
        return transcript

    async def get_latest_transcript(self, meeting_id: uuid.UUID) -> Transcript | None:
        result = await self.session.execute(
            select(Transcript)
            .where(Transcript.meeting_id == meeting_id)
            .order_by(Transcript.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
