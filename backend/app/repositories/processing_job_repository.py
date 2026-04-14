import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.processing_job import MeetingProcessingJob


class ProcessingJobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, job: MeetingProcessingJob) -> MeetingProcessingJob:
        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)
        return job

    async def save(self, job: MeetingProcessingJob) -> MeetingProcessingJob:
        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)
        return job

    async def get_by_id(self, job_id: uuid.UUID) -> MeetingProcessingJob | None:
        result = await self.session.execute(
            select(MeetingProcessingJob)
            .where(MeetingProcessingJob.id == job_id)
            .options(selectinload(MeetingProcessingJob.created_by))
        )
        return result.scalar_one_or_none()

    async def list_for_meeting(self, meeting_id: uuid.UUID) -> list[MeetingProcessingJob]:
        result = await self.session.execute(
            select(MeetingProcessingJob)
            .where(MeetingProcessingJob.meeting_id == meeting_id)
            .options(selectinload(MeetingProcessingJob.created_by))
            .order_by(MeetingProcessingJob.created_at.desc())
        )
        return list(result.scalars().all())
