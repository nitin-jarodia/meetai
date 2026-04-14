import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.search_chunk import MeetingSearchChunk


class SearchRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def replace_for_transcript(
        self, transcript_id: uuid.UUID, chunks: list[MeetingSearchChunk]
    ) -> None:
        await self.session.execute(
            delete(MeetingSearchChunk).where(
                MeetingSearchChunk.transcript_id == transcript_id
            )
        )
        for chunk in chunks:
            self.session.add(chunk)
        await self.session.flush()

    async def list_for_meeting_ids(
        self, meeting_ids: list[uuid.UUID]
    ) -> list[MeetingSearchChunk]:
        if not meeting_ids:
            return []
        result = await self.session.execute(
            select(MeetingSearchChunk)
            .where(MeetingSearchChunk.meeting_id.in_(meeting_ids))
            .order_by(
                MeetingSearchChunk.meeting_id.asc(),
                MeetingSearchChunk.chunk_index.asc(),
            )
        )
        return list(result.scalars().all())
