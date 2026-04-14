from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.processing_job import MeetingProcessingJob
from app.models.user import User
from app.repositories.processing_job_repository import ProcessingJobRepository
from app.services.ai_service import AIService
from app.services.meeting_service import (
    MeetingAccessDeniedError,
    MeetingNotFoundError,
    MeetingService,
)
from app.services.transcription_service import TranscriptionError
from app.websocket.manager import manager


class ProcessingJobNotFoundError(Exception):
    """Raised when the processing job cannot be found."""


class ProcessingRuntime:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def enqueue_audio_upload(
        self, meeting_id: uuid.UUID, user: User, filename: str | None, file_bytes: bytes
    ) -> MeetingProcessingJob:
        now = datetime.now(timezone.utc)
        settings.uploads_path.mkdir(parents=True, exist_ok=True)
        suffix = Path(filename or "").suffix or ".bin"
        temp_path = settings.uploads_path / f"{uuid.uuid4().hex}{suffix}"
        temp_path.write_bytes(file_bytes)

        async with self._session_factory() as session:
            service = MeetingService(session)
            await service._get_meeting_for_user(meeting_id, user)
            repo = ProcessingJobRepository(session)
            job = await repo.create(
                MeetingProcessingJob(
                    meeting_id=meeting_id,
                    created_by_id=user.id,
                    filename=filename,
                    status="queued",
                    stage="queued",
                    progress=0.0,
                    error_message=None,
                    created_at=now,
                    updated_at=now,
                    completed_at=None,
                )
            )
            await session.commit()
            hydrated_job = await repo.get_by_id(job.id)
            if not hydrated_job:
                raise ProcessingJobNotFoundError()

        task = asyncio.create_task(
            self._run_upload_job(job.id, meeting_id, user.id, temp_path)
        )
        self._tasks[str(job.id)] = task
        return hydrated_job

    async def get_job(self, job_id: uuid.UUID) -> MeetingProcessingJob:
        async with self._session_factory() as session:
            repo = ProcessingJobRepository(session)
            job = await repo.get_by_id(job_id)
            if not job:
                raise ProcessingJobNotFoundError()
            return job

    async def _set_job_state(
        self,
        session: AsyncSession,
        job: MeetingProcessingJob,
        *,
        status: str | None = None,
        stage: str | None = None,
        progress: float | None = None,
        error_message: str | None = None,
        completed: bool = False,
    ) -> MeetingProcessingJob:
        now = datetime.now(timezone.utc)
        if status is not None:
            job.status = status
        if stage is not None:
            job.stage = stage
        if progress is not None:
            job.progress = progress
        job.error_message = error_message
        job.updated_at = now
        if completed:
            job.completed_at = now
        repo = ProcessingJobRepository(session)
        await repo.save(job)
        await session.commit()
        await manager.broadcast_json(
            job.meeting_id,
            {
                "type": "job_updated",
                "job": {
                    "id": str(job.id),
                    "meeting_id": str(job.meeting_id),
                    "status": job.status,
                    "stage": job.stage,
                    "progress": job.progress,
                    "error_message": job.error_message,
                    "filename": job.filename,
                    "created_at": job.created_at.isoformat(),
                    "updated_at": job.updated_at.isoformat(),
                    "completed_at": (
                        job.completed_at.isoformat() if job.completed_at else None
                    ),
                },
            },
        )
        return job

    async def _run_upload_job(
        self, job_id: uuid.UUID, meeting_id: uuid.UUID, user_id: uuid.UUID, path: Path
    ) -> None:
        try:
            async with self._session_factory() as session:
                repo = ProcessingJobRepository(session)
                job = await repo.get_by_id(job_id)
                if not job:
                    return
                user = await session.get(User, user_id)
                if not user:
                    await self._set_job_state(
                        session,
                        job,
                        status="failed",
                        stage="failed",
                        progress=1.0,
                        error_message="User not found for processing job.",
                        completed=True,
                    )
                    return

                meeting_service = MeetingService(session)
                ai = AIService()

                await self._set_job_state(
                    session,
                    job,
                    status="processing",
                    stage="transcribing",
                    progress=0.1,
                )

                async def progress_callback(stage: str, progress: float) -> None:
                    await self._set_job_state(
                        session,
                        job,
                        status="processing",
                        stage=stage,
                        progress=progress,
                    )

                await meeting_service.process_audio_upload(
                    meeting_id,
                    user,
                    path,
                    ai,
                    progress_callback=progress_callback,
                )

                await self._set_job_state(
                    session,
                    job,
                    status="completed",
                    stage="completed",
                    progress=1.0,
                    completed=True,
                )
                await manager.broadcast_json(
                    meeting_id,
                    {
                        "type": "transcript_ready",
                        "meeting_id": str(meeting_id),
                        "job_id": str(job_id),
                    },
                )
        except (
            MeetingNotFoundError,
            MeetingAccessDeniedError,
            TranscriptionError,
            ValueError,
        ) as exc:
            async with self._session_factory() as session:
                repo = ProcessingJobRepository(session)
                job = await repo.get_by_id(job_id)
                if job:
                    await self._set_job_state(
                        session,
                        job,
                        status="failed",
                        stage="failed",
                        progress=1.0,
                        error_message=str(exc),
                        completed=True,
                    )
                    await manager.broadcast_json(
                        meeting_id,
                        {
                            "type": "job_failed",
                            "meeting_id": str(meeting_id),
                            "job_id": str(job_id),
                            "error": str(exc),
                        },
                    )
        finally:
            try:
                if path.is_file():
                    path.unlink()
            except OSError:
                pass
            self._tasks.pop(str(job_id), None)


runtime = ProcessingRuntime(AsyncSessionLocal)


def get_processing_runtime() -> ProcessingRuntime:
    return runtime
