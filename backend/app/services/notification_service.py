"""Email notifications.

Defaults to a no-op stub when SMTP is not configured so dev / tests never send
external mail. `aiosmtplib` is an optional dependency — missing it just logs.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from email.message import EmailMessage
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.meeting_action_item import MeetingActionItem
from app.models.notification_preference import NotificationPreference
from app.models.user import User

logger = logging.getLogger(__name__)


class NotificationService:
    """Thin abstraction so app code doesn't care if SMTP is wired up."""

    def __init__(self) -> None:
        self._enabled = bool(settings.smtp_host)
        if not self._enabled:
            logger.debug("SMTP not configured — email notifications are disabled.")

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def send_email(self, to: str, subject: str, body: str) -> bool:
        if not to:
            return False
        if not self._enabled:
            logger.info("Email skipped (SMTP disabled) to=%s subject=%s", to, subject)
            return False
        try:
            import aiosmtplib  # type: ignore
        except ImportError:
            logger.warning("aiosmtplib not installed; cannot send email to %s", to)
            return False

        message = EmailMessage()
        message["From"] = settings.smtp_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username or None,
                password=settings.smtp_password or None,
                start_tls=settings.smtp_use_tls,
            )
            return True
        except Exception as exc:  # pragma: no cover
            logger.warning("SMTP send failed to %s: %s", to, exc)
            return False

    async def notify_action_item_due(
        self,
        session: AsyncSession,
        item: MeetingActionItem,
    ) -> None:
        recipient = await self._resolve_recipient(session, item)
        if not recipient:
            return
        if not await _is_reminder_enabled(session, recipient):
            return
        due_text = _format_due(item.due_at)
        subject = f"[MeetAI] Action item due: {item.task[:80]}"
        body = (
            f"Hi {recipient.full_name or recipient.email},\n\n"
            f"This is a reminder for the following action item:\n\n"
            f"  {item.task}\n\n"
            f"Due: {due_text}\n"
            f"Status: {item.status}\n\n"
            "You can update it in MeetAI.\n"
        )
        await self.send_email(recipient.email, subject, body)

    async def _resolve_recipient(
        self, session: AsyncSession, item: MeetingActionItem
    ) -> User | None:
        if item.assigned_user_id:
            result = await session.execute(
                select(User).where(User.id == item.assigned_user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                return user
        if item.created_by_id:
            result = await session.execute(
                select(User).where(User.id == item.created_by_id)
            )
            return result.scalar_one_or_none()
        return None


async def _is_reminder_enabled(session: AsyncSession, user: User) -> bool:
    result = await session.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user.id)
    )
    pref = result.scalar_one_or_none()
    if pref is None:
        return True
    return pref.email_enabled and pref.reminders_enabled


def _format_due(when: datetime | None) -> str:
    if not when:
        return "(no deadline)"
    return when.strftime("%Y-%m-%d %H:%M UTC")


def notification_recipients(users: Iterable[User]) -> list[str]:
    """Strip duplicates / empty emails so SMTP doesn't choke on headers."""
    seen: set[str] = set()
    out: list[str] = []
    for user in users:
        email = (user.email or "").strip().lower()
        if not email or email in seen:
            continue
        seen.add(email)
        out.append(email)
    return out


_notification_singleton: NotificationService | None = None


def get_notification_service() -> NotificationService:
    global _notification_singleton
    if _notification_singleton is None:
        _notification_singleton = NotificationService()
    return _notification_singleton
