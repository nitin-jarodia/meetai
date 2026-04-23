from __future__ import annotations

import asyncio
import logging
import mimetypes
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

logger = logging.getLogger(__name__)


class ProcessingJobNotFoundError(Exception):
    """Raised when the processing job cannot be found."""


def _persist_audio(
    meeting_id: uuid.UUID, filename: str | None, file_bytes: bytes
) -> tuple[Path, str | None]:
    """Persist the uploaded audio under uploads/audio/<meeting_id>/ and return
    (path, mime_type). When PERSIST_AUDIO is disabled, writes to a temp file
    that the job cleans up afterward.
    """
    suffix = Path(filename or "").suffix or ".bin"
    if settings.persist_audio:
        dest_dir = settings.audio_path / str(meeting_id)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{uuid.uuid4().hex}{suffix}"
    else:
        settings.uploads_path.mkdir(parents=True, exist_ok=True)
        dest = settings.uploads_path / f"{uuid.uuid4().hex}{suffix}"
    dest.write_bytes(file_bytes)
    mime, _ = mimetypes.guess_type(filename or dest.name)
    return dest, mime


class ProcessingRuntime:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._arq_pool = None  # type: ignore[assignment]

    async def _ensure_arq_pool(self):
        """Create the Arq pool lazily; return None when Redis isn't configured."""
        if not settings.arq_redis_url:
            return None
        if self._arq_pool is not None:
            return self._arq_pool
        try:
            from arq import create_pool  # type: ignore
            from arq.connections import RedisSettings  # type: ignore

            self._arq_pool = await create_pool(
                RedisSettings.from_dsn(settings.arq_redis_url)
            )
            logger.info("Connected to Arq redis: %s", settings.arq_redis_url)
            return self._arq_pool
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "Arq unavailable (%s); falling back to in-process worker.", exc
            )
            return None

    async def enqueue_audio_upload(
        self, meeting_id: uuid.UUID, user: User, filename: str | None, file_bytes: bytes
    ) -> MeetingProcessingJob:
        now = datetime.now(timezone.utc)
        saved_path, mime_type = _persist_audio(meeting_id, filename, file_bytes)

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

        pool = await self._ensure_arq_pool()
        if pool is not None:
            try:
                await pool.enqueue_job(
                    "process_audio_job",
                    str(job.id),
                    str(meeting_id),
                    str(user.id),
                    str(saved_path),
                    mime_type,
                    settings.persist_audio,
                )
                return hydrated_job
            except Exception as exc:  # pragma: no cover
                logger.warning(
                    "Arq enqueue failed (%s); running in-process instead.", exc
                )

        task = asyncio.create_task(
            run_upload_job(
                self._session_factory,
                job.id,
                meeting_id,
                user.id,
                saved_path,
                mime_type,
                persisted=settings.persist_audio,
            )
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

    async def close(self) -> None:
        if self._arq_pool is not None:
            try:
                await self._arq_pool.close()
            except Exception:  # pragma: no cover
                pass
            self._arq_pool = None


async def _set_job_state(
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


async def run_upload_job(
    session_factory: async_sessionmaker[AsyncSession],
    job_id: uuid.UUID,
    meeting_id: uuid.UUID,
    user_id: uuid.UUID,
    path: Path,
    audio_mime_type: str | None,
    *,
    persisted: bool,
) -> None:
    """Process a single audio upload job.

    Shared code path for the in-process runtime and the Arq worker.
    """
    try:
        async with session_factory() as session:
            repo = ProcessingJobRepository(session)
            job = await repo.get_by_id(job_id)
            if not job:
                return
            user = await session.get(User, user_id)
            if not user:
                await _set_job_state(
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

            await _set_job_state(
                session,
                job,
                status="processing",
                stage="transcribing",
                progress=0.1,
            )

            async def progress_callback(stage: str, progress: float) -> None:
                await _set_job_state(
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
                persistent_audio_path=path if persisted else None,
                audio_mime_type=audio_mime_type,
                progress_callback=progress_callback,
            )

            await _set_job_state(
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
        async with session_factory() as session:
            repo = ProcessingJobRepository(session)
            job = await repo.get_by_id(job_id)
            if job:
                await _set_job_state(
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
        if not persisted:
            try:
                if path.is_file():
                    path.unlink()
            except OSError:
                pass


runtime = ProcessingRuntime(AsyncSessionLocal)


def get_processing_runtime() -> ProcessingRuntime:
    return runtime
