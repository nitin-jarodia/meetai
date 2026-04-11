import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.meeting import Meeting
from app.models.participant import Participant
from app.models.transcript import Transcript


class MeetingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, meeting_id: uuid.UUID) -> Meeting | None:
        result = await self.session.execute(
            select(Meeting)
            .where(Meeting.id == meeting_id)
            .options(
                selectinload(Meeting.host),
                selectinload(Meeting.participants).selectinload(Participant.user),
                selectinload(Meeting.transcripts),
            )
        )
        return result.scalar_one_or_none()

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
