import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.meeting import ActionItemOut, ActionItemUpdateRequest
from app.services.action_item_service import (
    ActionItemAccessDeniedError,
    ActionItemNotFoundError,
    ActionItemService,
    ActionItemUpdate,
)
from app.services.meeting_service import serialize_action_item

router = APIRouter(prefix="/action-items", tags=["action-items"])


@router.patch("/{item_id}", response_model=ActionItemOut)
async def update_action_item(
    item_id: uuid.UUID,
    body: ActionItemUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ActionItemService(db)
    try:
        item = await service.update_item(
            item_id,
            current_user,
            ActionItemUpdate(
                task=body.task,
                status=body.status,
                deadline=body.deadline,
                assigned_to_name=body.assigned_to_name,
                assigned_user_id=body.assigned_user_id,
            ),
        )
    except ActionItemNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action item not found",
        ) from None
    except ActionItemAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this action item",
        ) from None
    return serialize_action_item(item)
