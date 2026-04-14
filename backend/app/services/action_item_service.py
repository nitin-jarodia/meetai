from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meeting import Meeting
from app.models.meeting_action_item import MeetingActionItem
from app.models.transcript import Transcript
from app.models.user import User
from app.repositories.action_item_repository import ActionItemRepository
from app.repositories.meeting_repository import MeetingRepository
from app.services.ai_service import ActionItem as AIActionItem


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
            item.deadline = updates.deadline.strip() or None
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

        record = MeetingActionItem(
            meeting_id=meeting.id,
            transcript_id=transcript.id,
            created_by_id=meeting.host_id,
            assigned_user_id=assigned_user_id,
            task=item.task,
            assigned_to_name=assigned_to_name,
            deadline=item.deadline,
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
            "status": item.status,
            "id": str(item.id),
        }
        for item in created
    ]
    session.add(transcript)
    await session.flush()
    return created
