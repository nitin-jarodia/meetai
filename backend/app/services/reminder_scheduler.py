"""Background scheduler that emits "due-soon" reminders.

Uses APScheduler's AsyncIOScheduler when available; otherwise falls back to a
plain asyncio polling loop. Both paths go through the same
``run_reminder_sweep`` function, which:

1. Finds open action items whose ``due_at`` is within the lead window
2. Broadcasts an ``action_item_due_soon`` WebSocket event to meeting rooms
3. Sends an email via :class:`NotificationService` (no-op when SMTP is unset)
4. Also emits ``action_item_overdue`` for items past due
5. Debounces itself via ``last_reminded_at`` so users aren't spammed
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.meeting_action_item import MeetingActionItem
from app.services.notification_service import get_notification_service
from app.websocket.manager import manager

logger = logging.getLogger(__name__)

_REMINDER_DEBOUNCE = timedelta(hours=6)


def _isoformat(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


async def _broadcast_item(item: MeetingActionItem, event_type: str) -> None:
    await manager.broadcast_json(
        item.meeting_id,
        {
            "type": event_type,
            "action_item": {
                "id": str(item.id),
                "meeting_id": str(item.meeting_id),
                "task": item.task,
                "status": item.status,
                "assigned_to": item.assigned_to_name,
                "assigned_user_id": (
                    str(item.assigned_user_id) if item.assigned_user_id else None
                ),
                "due_at": _isoformat(item.due_at),
                "deadline": item.deadline,
            },
        },
    )


async def run_reminder_sweep(session_factory: async_sessionmaker[AsyncSession]) -> None:
    now = datetime.now(timezone.utc)
    lead = timedelta(minutes=max(1, settings.reminder_lead_time_minutes))
    upper = now + lead
    debounce_cutoff = now - _REMINDER_DEBOUNCE

    async with session_factory() as session:
        stmt = (
            select(MeetingActionItem)
            .where(
                MeetingActionItem.due_at.is_not(None),
                MeetingActionItem.status != "completed",
                MeetingActionItem.status != "done",
                MeetingActionItem.status != "cancelled",
                MeetingActionItem.due_at <= upper,
                or_(
                    MeetingActionItem.last_reminded_at.is_(None),
                    MeetingActionItem.last_reminded_at < debounce_cutoff,
                ),
            )
            .options(selectinload(MeetingActionItem.assigned_user))
            .limit(100)
        )
        result = await session.execute(stmt)
        items = list(result.scalars().all())

        if not items:
            return

        notifier = get_notification_service()
        for item in items:
            event = "action_item_overdue" if item.due_at < now else "action_item_due_soon"
            try:
                await _broadcast_item(item, event)
            except Exception as exc:  # pragma: no cover
                logger.warning("Reminder broadcast failed for %s: %s", item.id, exc)
            try:
                await notifier.notify_action_item_due(session, item)
            except Exception as exc:  # pragma: no cover
                logger.warning("Reminder email failed for %s: %s", item.id, exc)
            item.last_reminded_at = now

        await session.commit()


class ReminderScheduler:
    """Encapsulates start/stop so lifespan owns the lifecycle."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._scheduler = None  # type: ignore[assignment]
        self._fallback_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        interval = max(5, settings.reminder_poll_interval_seconds)
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore

            scheduler = AsyncIOScheduler(timezone="UTC")
            scheduler.add_job(
                run_reminder_sweep,
                "interval",
                args=[self._session_factory],
                seconds=interval,
                id="meetai.reminders",
                replace_existing=True,
                coalesce=True,
                max_instances=1,
                next_run_time=datetime.now(timezone.utc) + timedelta(seconds=5),
            )
            scheduler.start()
            self._scheduler = scheduler
            logger.info("ReminderScheduler started (APScheduler, every %ss)", interval)
            return
        except ImportError:
            logger.info(
                "APScheduler not installed; using asyncio polling every %ss.", interval
            )

        async def loop() -> None:
            try:
                await asyncio.sleep(5)
                while True:
                    try:
                        await run_reminder_sweep(self._session_factory)
                    except Exception as exc:  # pragma: no cover
                        logger.warning("Reminder sweep failed: %s", exc)
                    await asyncio.sleep(interval)
            except asyncio.CancelledError:
                pass

        self._fallback_task = asyncio.create_task(loop())

    async def stop(self) -> None:
        if self._scheduler is not None:
            try:
                self._scheduler.shutdown(wait=False)
            except Exception:  # pragma: no cover
                pass
            self._scheduler = None
        if self._fallback_task is not None:
            self._fallback_task.cancel()
            try:
                await self._fallback_task
            except (asyncio.CancelledError, Exception):  # pragma: no cover
                pass
            self._fallback_task = None


_scheduler_singleton: ReminderScheduler | None = None


def get_scheduler() -> ReminderScheduler:
    global _scheduler_singleton
    if _scheduler_singleton is None:
        _scheduler_singleton = ReminderScheduler(AsyncSessionLocal)
    return _scheduler_singleton
