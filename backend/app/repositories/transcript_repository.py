import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment


class TranscriptRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, transcript_id: uuid.UUID) -> Transcript | None:
        result = await self.session.execute(
            select(Transcript).where(Transcript.id == transcript_id)
        )
        return result.scalar_one_or_none()

    async def get_with_segments(self, transcript_id: uuid.UUID) -> Transcript | None:
        result = await self.session.execute(
            select(Transcript)
            .options(selectinload(Transcript.segments))
            .where(Transcript.id == transcript_id)
        )
        return result.scalar_one_or_none()

    async def save(self, transcript: Transcript) -> Transcript:
        self.session.add(transcript)
        await self.session.flush()
        await self.session.refresh(transcript)
        return transcript

    async def replace_segments(
        self,
        transcript_id: uuid.UUID,
        segments: list[TranscriptSegment],
    ) -> None:
        await self.session.execute(
            delete(TranscriptSegment).where(
                TranscriptSegment.transcript_id == transcript_id
            )
        )
        for seg in segments:
            self.session.add(seg)
        await self.session.flush()
