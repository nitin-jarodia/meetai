"""Arq worker definitions for background audio processing.

Run with:
    cd backend
    arq app.worker.arq_worker.WorkerSettings

Requires ARQ_REDIS_URL in .env. The API falls back to in-process processing
when Redis isn't reachable, so this worker is purely an opt-in performance /
scale upgrade.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.processing_service import run_upload_job

logger = logging.getLogger(__name__)


async def process_audio_job(
    ctx: dict[str, Any],
    job_id: str,
    meeting_id: str,
    user_id: str,
    path: str,
    audio_mime_type: str | None,
    persisted: bool,
) -> None:
    await run_upload_job(
        AsyncSessionLocal,
        uuid.UUID(job_id),
        uuid.UUID(meeting_id),
        uuid.UUID(user_id),
        Path(path),
        audio_mime_type,
        persisted=persisted,
    )


def _build_redis_settings():
    from arq.connections import RedisSettings  # type: ignore

    if not settings.arq_redis_url:
        raise RuntimeError(
            "ARQ_REDIS_URL is not set. Export it in backend/.env to run the worker."
        )
    return RedisSettings.from_dsn(settings.arq_redis_url)


async def _on_startup(ctx: dict[str, Any]) -> None:  # pragma: no cover
    logger.info("Arq worker started.")


async def _on_shutdown(ctx: dict[str, Any]) -> None:  # pragma: no cover
    logger.info("Arq worker stopped.")


class WorkerSettings:
    """Arq worker config. `redis_settings` is resolved at class-definition time."""

    functions = [process_audio_job]
    keep_result = 60
    max_jobs = 4
    on_startup = _on_startup
    on_shutdown = _on_shutdown

    # When ARQ_REDIS_URL is unset we still want this module to import cleanly
    # (so the API can reference it). The worker CLI itself will call
    # `_build_redis_settings()` below and raise the proper error if unset.
    try:
        redis_settings = _build_redis_settings()
    except Exception:  # pragma: no cover
        redis_settings = None  # type: ignore[assignment]
