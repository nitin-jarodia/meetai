from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meeting import Meeting
from app.models.meeting_action_item import MeetingActionItem
from app.models.transcript import Transcript
from app.models.user import User
from app.repositories.action_item_repository import ActionItemRepository
from app.repositories.meeting_repository import MeetingRepository
from app.services.ai_service import ActionItem as AIActionItem
from app.services.deadline_parser import parse_due_at


_SENTINEL = object()


class ActionItemNotFoundError(Exception):
    """Raised when the action item does not exist."""


class ActionItemAccessDeniedError(Exception):
    """Raised when the user cannot access the action item's meeting."""


@dataclass(slots=True)
class ActionItemUpdate:
    task: str | None = None
    status: str | None = None
    deadline: str | None = None
    assigned_to_name: str | None = None
    assigned_user_id: uuid.UUID | None = None
    # `due_at` uses a sentinel so callers can distinguish "not provided"
    # (leave alone) from "clear this field" (pass None explicitly).
    due_at: datetime | None | object = field(default=_SENTINEL)


class ActionItemService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.items = ActionItemRepository(session)
        self.meetings = MeetingRepository(session)

    async def _get_item_for_user(
        self, item_id: uuid.UUID, user: User
    ) -> MeetingActionItem:
        item = await self.items.get_by_id(item_id)
        if not item:
            raise ActionItemNotFoundError()
        meeting = await self.meetings.get_by_id(item.meeting_id)
        if not meeting:
            raise ActionItemNotFoundError()
        if meeting.host_id == user.id:
            return item
        if await self.meetings.get_participant(meeting.id, user.id):
            return item
        raise ActionItemAccessDeniedError()

    async def update_item(
        self, item_id: uuid.UUID, user: User, updates: ActionItemUpdate
    ) -> MeetingActionItem:
        item = await self._get_item_for_user(item_id, user)
        if updates.task is not None:
            item.task = updates.task.strip()
        if updates.status is not None:
            item.status = updates.status
        if updates.deadline is not None:
            deadline_text = updates.deadline.strip() or None
            item.deadline = deadline_text
            # If the caller didn't also explicitly set due_at, re-parse it from
            # the human string so both fields stay consistent.
            if updates.due_at is _SENTINEL:
                item.due_at = parse_due_at(deadline_text)
                item.last_reminded_at = None
        if updates.due_at is not _SENTINEL:
            new_due = updates.due_at  # type: ignore[assignment]
            if isinstance(new_due, datetime) and new_due.tzinfo is None:
                new_due = new_due.replace(tzinfo=timezone.utc)
            item.due_at = new_due  # type: ignore[assignment]
            item.last_reminded_at = None
        if updates.assigned_to_name is not None:
            item.assigned_to_name = updates.assigned_to_name.strip() or None
            if updates.assigned_user_id is None:
                item.assigned_user_id = None
        if updates.assigned_user_id is not None:
            item.assigned_user_id = updates.assigned_user_id
        item.updated_at = datetime.now(timezone.utc)
        await self.items.save(item)
        return item


async def sync_ai_action_items(
    session: AsyncSession,
    meeting: Meeting,
    transcript: Transcript,
    action_items: list[AIActionItem],
) -> list[MeetingActionItem]:
    repo = ActionItemRepository(session)
    await repo.delete_ai_items_for_transcript(transcript.id)

    now = datetime.now(timezone.utc)
    created: list[MeetingActionItem] = []
    for item in action_items:
        assigned_user_id = None
        assigned_to_name = item.assigned_to
        if item.assigned_to:
            normalized = item.assigned_to.strip().lower()
            for participant in meeting.participants:
                user = participant.user
                if not user:
                    continue
                candidates = [user.email.lower()]
                if user.full_name:
                    candidates.append(user.full_name.lower())
                if normalized in candidates:
                    assigned_user_id = user.id
                    assigned_to_name = user.full_name or user.email
                    break

        due_at = parse_due_at(item.deadline, reference=now)
        record = MeetingActionItem(
            meeting_id=meeting.id,
            transcript_id=transcript.id,
            created_by_id=meeting.host_id,
            assigned_user_id=assigned_user_id,
            task=item.task,
            assigned_to_name=assigned_to_name,
            deadline=item.deadline,
            due_at=due_at,
            status="open",
            source="ai",
            created_at=now,
            updated_at=now,
        )
        await repo.save(record)
        created.append(record)

    transcript.action_items = [
        {
            "task": item.task,
            "assigned_to": item.assigned_to_name,
            "deadline": item.deadline,
            "due_at": item.due_at.isoformat() if item.due_at else None,
            "status": item.status,
            "id": str(item.id),
        }
        for item in created
    ]
    session.add(transcript)
    await session.flush()
    return created
