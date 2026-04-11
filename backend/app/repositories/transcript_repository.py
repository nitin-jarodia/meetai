import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transcript import Transcript


class TranscriptRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, transcript_id: uuid.UUID) -> Transcript | None:
        result = await self.session.execute(
            select(Transcript).where(Transcript.id == transcript_id)
        )
        return result.scalar_one_or_none()

    async def save(self, transcript: Transcript) -> Transcript:
        self.session.add(transcript)
        await self.session.flush()
        await self.session.refresh(transcript)
        return transcript
