import mimetypes
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_user_flexible
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.meeting import (
    TranscriptRegenerateResponse,
    TranscriptSegmentOut,
    TranscriptSegmentsResponse,
    TranscriptTranslationResponse,
    TranscriptUpdateRequest,
    TranscriptUpdateResponse,
)
from app.services.ai_service import AIService, get_ai_service
from app.services.transcript_service import (
    TranscriptAccessDeniedError,
    TranscriptNotFoundError,
    TranscriptService,
)
from app.services.translation_service import (
    TranscriptAccessDeniedError as TranslationAccessDeniedError,
    TranscriptNotFoundError as TranslationTranscriptNotFoundError,
    TranslationError,
    TranslationService,
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
    from app.services.meeting_service import serialize_transcript

    brief = serialize_transcript(transcript)
    return TranscriptRegenerateResponse(**brief.model_dump())


@router.get(
    "/{transcript_id}/segments",
    response_model=TranscriptSegmentsResponse,
)
async def list_transcript_segments(
    transcript_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TranscriptService(db)
    try:
        transcript = await service.get_transcript_with_segments(
            transcript_id, current_user
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
    return TranscriptSegmentsResponse(
        transcript_id=transcript.id,
        language=transcript.language,
        duration_ms=transcript.duration_ms,
        has_audio=bool(transcript.audio_path),
        segments=[TranscriptSegmentOut.model_validate(seg) for seg in transcript.segments],
    )


@router.get("/{transcript_id}/audio")
async def stream_transcript_audio(
    transcript_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """Stream the original uploaded audio so the frontend can do click-to-seek playback."""
    service = TranscriptService(db)
    try:
        transcript = await service.get_transcript_with_segments(
            transcript_id, current_user
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

    if not transcript.audio_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No stored audio for this transcript",
        )

    candidate = Path(transcript.audio_path)
    if not candidate.is_absolute():
        candidate = (settings.backend_root / candidate).resolve()

    # Security: keep everything inside the configured uploads dir.
    try:
        candidate.relative_to(settings.uploads_path.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file no longer available",
        ) from None

    if not candidate.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file no longer available",
        )

    media_type = transcript.audio_mime_type
    if not media_type:
        media_type, _ = mimetypes.guess_type(candidate.name)
        media_type = media_type or "application/octet-stream"

    return FileResponse(path=candidate, media_type=media_type, filename=candidate.name)


@router.post(
    "/{transcript_id}/translate",
    response_model=TranscriptTranslationResponse,
)
async def translate_transcript(
    transcript_id: uuid.UUID,
    target: str = Query(min_length=2, max_length=16, description="ISO 639-1 code, e.g. en"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TranslationService(db)
    try:
        result = await service.translate(transcript_id, current_user, target)
    except TranslationTranscriptNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found",
        ) from None
    except TranslationAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this transcript",
        ) from None
    except TranslationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return TranscriptTranslationResponse(
        transcript_id=result.transcript_id,
        target_language=result.target_language,
        translated_text=result.text,
    )
