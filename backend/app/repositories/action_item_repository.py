import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.meeting_action_item import MeetingActionItem


class ActionItemRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_meeting(self, meeting_id: uuid.UUID) -> list[MeetingActionItem]:
        result = await self.session.execute(
            select(MeetingActionItem)
            .where(MeetingActionItem.meeting_id == meeting_id)
            .options(selectinload(MeetingActionItem.assigned_user))
            .order_by(MeetingActionItem.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, item_id: uuid.UUID) -> MeetingActionItem | None:
        result = await self.session.execute(
            select(MeetingActionItem)
            .where(MeetingActionItem.id == item_id)
            .options(selectinload(MeetingActionItem.assigned_user))
        )
        return result.scalar_one_or_none()

    async def save(self, item: MeetingActionItem) -> MeetingActionItem:
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def delete_ai_items_for_transcript(self, transcript_id: uuid.UUID) -> None:
        result = await self.session.execute(
            select(MeetingActionItem).where(
                MeetingActionItem.transcript_id == transcript_id,
                MeetingActionItem.source == "ai",
            )
        )
        for item in result.scalars().all():
            await self.session.delete(item)
