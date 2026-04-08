import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.meeting import (
    AudioUploadResponse,
    MeetingCreate,
    MeetingDetail,
    MeetingOut,
)
from app.services.ai_service import AIService, SummaryGenerationError, get_ai_service
from app.services.meeting_service import (
    MeetingAccessDeniedError,
    MeetingNotFoundError,
    MeetingService,
)
from app.services.transcription_service import TranscriptionError

router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.post("", response_model=MeetingOut, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    data: MeetingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = MeetingService(db)
    return await service.create_meeting(current_user, data)


@router.post("/{meeting_id}/join", response_model=MeetingOut)
async def join_meeting(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = MeetingService(db)
    try:
        return await service.join_meeting(meeting_id, current_user)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")


@router.get("/{meeting_id}", response_model=MeetingDetail)
async def get_meeting(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = MeetingService(db)
    detail = await service.get_meeting_detail(meeting_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    return detail


@router.post(
    "/{meeting_id}/upload-audio",
    response_model=AudioUploadResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_meeting_audio(
    meeting_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ai: AIService = Depends(get_ai_service),
):
    """Upload audio, transcribe with local Whisper, summarize with Groq, store transcript."""
    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file",
        )

    dest: Path | None = None
    try:
        settings.uploads_path.mkdir(parents=True, exist_ok=True)
        ext = Path(file.filename or "").suffix or ".bin"
        dest = settings.uploads_path / f"{uuid.uuid4().hex}{ext}"
        dest.write_bytes(contents)
        service = MeetingService(db)
        try:
            transcript, summary = await service.process_audio_upload(
                meeting_id, current_user, dest, ai
            )
        except MeetingNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found",
            ) from None
        except MeetingAccessDeniedError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not allowed to access this meeting",
            ) from None
        except TranscriptionError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(e),
            ) from e
        except SummaryGenerationError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(e),
            ) from e
        return AudioUploadResponse(transcript=transcript, summary=summary)
    finally:
        if dest is not None:
            try:
                if dest.is_file():
                    dest.unlink()
            except OSError:
                pass
