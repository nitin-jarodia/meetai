import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.meeting import (
    AudioUploadResponse,
    MeetingCreate,
    MeetingDetail,
    MeetingExportResponse,
    MeetingListResponse,
    MeetingProcessingJobOut,
    MeetingQuestionRequest,
    MeetingQuestionResponse,
    MeetingOut,
    MeetingSearchResponse,
)
from app.services.ai_service import AIService, get_ai_service
from app.services.processing_service import (
    ProcessingJobNotFoundError,
    ProcessingRuntime,
    get_processing_runtime,
)
from app.services.meeting_service import (
    MeetingAccessDeniedError,
    MeetingAnswer,
    MeetingNotFoundError,
    MeetingService,
    TranscriptNotFoundError,
    serialize_job,
)

router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.get("", response_model=MeetingListResponse)
async def list_meetings(
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = MeetingService(db)
    return await service.list_meetings(current_user, query=q, limit=limit)


@router.get("/search", response_model=MeetingSearchResponse)
async def search_meetings(
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.search_service import SearchService

    service = SearchService(db)
    results = await service.search_meetings(current_user, q, limit=limit)
    return MeetingSearchResponse(
        items=[
            {
                "meeting": {
                    "id": result.meeting.id,
                    "title": result.meeting.title,
                    "description": result.meeting.description,
                    "host_id": result.meeting.host_id,
                    "created_at": result.meeting.created_at,
                },
                "score": result.score,
                "snippet": result.snippet,
            }
            for result in results
        ]
    )


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
    try:
        detail = await service.get_meeting_detail(meeting_id, current_user)
    except MeetingNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    except MeetingAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this meeting",
        ) from None
    return detail


@router.get("/jobs/{job_id}", response_model=MeetingProcessingJobOut)
async def get_processing_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    runtime: ProcessingRuntime = Depends(get_processing_runtime),
):
    try:
        job = await runtime.get_job(job_id)
        await MeetingService(db).get_meeting_detail(job.meeting_id, current_user)
        return serialize_job(job)
    except ProcessingJobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Processing job not found",
        ) from None
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


@router.get("/{meeting_id}/jobs", response_model=list[MeetingProcessingJobOut])
async def list_meeting_jobs(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        detail = await MeetingService(db).get_meeting_detail(meeting_id, current_user)
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
    return detail.processing_jobs


@router.post(
    "/{meeting_id}/ask",
    response_model=MeetingQuestionResponse,
    status_code=status.HTTP_200_OK,
)
async def ask_meeting_question(
    meeting_id: uuid.UUID,
    body: MeetingQuestionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ai: AIService = Depends(get_ai_service),
):
    service = MeetingService(db)
    try:
        result: MeetingAnswer = await service.ask_meeting_question(
            meeting_id, current_user, body.question, ai
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
    except TranscriptNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No transcript found for this meeting",
        ) from None
    return MeetingQuestionResponse(answer=result.answer, entry=result.entry)


@router.post(
    "/{meeting_id}/upload-audio",
    response_model=AudioUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_meeting_audio(
    meeting_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    runtime: ProcessingRuntime = Depends(get_processing_runtime),
):
    """Upload audio and queue background processing."""
    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file",
        )

    try:
        job = await runtime.enqueue_audio_upload(
            meeting_id, current_user, file.filename, contents
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
    return AudioUploadResponse(job=serialize_job(job))


@router.get(
    "/{meeting_id}/export",
    response_model=MeetingExportResponse,
    status_code=status.HTTP_200_OK,
)
async def export_meeting(
    meeting_id: uuid.UUID,
    format: str = Query(default="markdown"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = MeetingService(db)
    try:
        return await service.export_meeting(meeting_id, current_user, format)
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
