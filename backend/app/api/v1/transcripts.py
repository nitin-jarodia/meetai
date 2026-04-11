import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.meeting import (
    TranscriptRegenerateResponse,
    TranscriptUpdateRequest,
    TranscriptUpdateResponse,
)
from app.services.ai_service import AIService, get_ai_service
from app.services.transcript_service import (
    TranscriptAccessDeniedError,
    TranscriptNotFoundError,
    TranscriptService,
)

router = APIRouter(prefix="/transcripts", tags=["transcripts"])


@router.put("/{transcript_id}", response_model=TranscriptUpdateResponse)
async def update_transcript(
    transcript_id: uuid.UUID,
    body: TranscriptUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TranscriptService(db)
    try:
        result = await service.update_cleaned_transcript(
            transcript_id, current_user, body.cleaned_transcript
        )
    except TranscriptNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found",
        ) from None
    except TranscriptAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this transcript",
        ) from None
    return TranscriptUpdateResponse(message=result.message)


@router.post(
    "/{transcript_id}/regenerate",
    response_model=TranscriptRegenerateResponse,
    status_code=status.HTTP_200_OK,
)
async def regenerate_transcript_summary(
    transcript_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ai: AIService = Depends(get_ai_service),
):
    service = TranscriptService(db)
    try:
        transcript = await service.regenerate_transcript_summary(
            transcript_id, current_user, ai
        )
    except TranscriptNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found",
        ) from None
    except TranscriptAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this transcript",
        ) from None
    return TranscriptRegenerateResponse.model_validate(transcript)
