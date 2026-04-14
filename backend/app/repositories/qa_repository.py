import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.meeting_qa import MeetingQAEntry


class QARepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, entry: MeetingQAEntry) -> MeetingQAEntry:
        self.session.add(entry)
        await self.session.flush()
        await self.session.refresh(entry)
        return entry

    async def list_for_meeting(self, meeting_id: uuid.UUID) -> list[MeetingQAEntry]:
        result = await self.session.execute(
            select(MeetingQAEntry)
            .where(MeetingQAEntry.meeting_id == meeting_id)
            .options(selectinload(MeetingQAEntry.user))
            .order_by(MeetingQAEntry.created_at.desc())
        )
        return list(result.scalars().all())
