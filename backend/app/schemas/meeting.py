import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.user import UserOut


class MeetingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None


class MeetingOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    host_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class ParticipantBrief(BaseModel):
    user_id: uuid.UUID
    role: str
    joined_at: datetime
    user: UserOut

    model_config = {"from_attributes": True}


class ActionItemOut(BaseModel):
    id: uuid.UUID | None = None
    task: str
    assigned_to: str | None = None
    deadline: str | None = None
    due_at: datetime | None = None
    status: str | None = None
    assigned_user_id: uuid.UUID | None = None
    source: str | None = None
    updated_at: datetime | None = None


class MeetingQAEntryOut(BaseModel):
    id: uuid.UUID
    transcript_id: uuid.UUID | None = None
    question: str
    answer: str
    created_at: datetime
    asked_by: UserOut


class MeetingProcessingJobOut(BaseModel):
    id: uuid.UUID
    meeting_id: uuid.UUID
    filename: str | None = None
    status: str
    stage: str
    progress: float
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    created_by: UserOut


class TranscriptSegmentOut(BaseModel):
    id: uuid.UUID
    order_index: int
    start_ms: int
    end_ms: int
    text: str
    speaker_label: str
    confidence: float | None = None

    model_config = {"from_attributes": True}


class TranscriptBrief(BaseModel):
    id: uuid.UUID
    transcript_text: str
    cleaned_transcript: str | None = None
    translated_text: str | None = None
    translated_language: str | None = None
    summary: str | None = None
    key_points: list[str] = Field(default_factory=list)
    action_items: list[ActionItemOut] = Field(default_factory=list)
    language: str | None = None
    duration_ms: int | None = None
    audio_path: str | None = None
    has_audio: bool = False
    segment_index: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MeetingDetail(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    host_id: uuid.UUID
    created_at: datetime
    host: UserOut
    participants: list[ParticipantBrief]
    transcripts: list[TranscriptBrief]
    qa_history: list[MeetingQAEntryOut] = Field(default_factory=list)
    action_items: list[ActionItemOut] = Field(default_factory=list)
    processing_jobs: list[MeetingProcessingJobOut] = Field(default_factory=list)


class MeetingListResponse(BaseModel):
    items: list[MeetingDetail] = Field(default_factory=list)


class MeetingSearchResultOut(BaseModel):
    meeting: MeetingOut
    score: float
    snippet: str


class MeetingSearchResponse(BaseModel):
    items: list[MeetingSearchResultOut] = Field(default_factory=list)


class AudioUploadResponse(BaseModel):
    job: MeetingProcessingJobOut


class TranscriptUpdateRequest(BaseModel):
    cleaned_transcript: str = Field(min_length=1)

    @field_validator("cleaned_transcript", mode="before")
    @classmethod
    def _strip_cleaned_transcript(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return value.strip()


class TranscriptUpdateResponse(BaseModel):
    message: str


class TranscriptRegenerateResponse(TranscriptBrief):
    pass


class TranscriptSegmentsResponse(BaseModel):
    transcript_id: uuid.UUID
    language: str | None = None
    duration_ms: int | None = None
    has_audio: bool = False
    segments: list[TranscriptSegmentOut] = Field(default_factory=list)


class TranscriptTranslationResponse(BaseModel):
    transcript_id: uuid.UUID
    target_language: str
    translated_text: str


class MeetingQuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

    @field_validator("question", mode="before")
    @classmethod
    def _strip_question(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return value.strip()


class MeetingQuestionResponse(BaseModel):
    answer: str
    entry: MeetingQAEntryOut


class ActionItemUpdateRequest(BaseModel):
    task: str | None = Field(default=None, min_length=1, max_length=5000)
    assigned_to_name: str | None = Field(default=None, max_length=255)
    assigned_user_id: uuid.UUID | None = None
    deadline: str | None = Field(default=None, max_length=255)
    due_at: datetime | None = None
    status: str | None = Field(default=None, max_length=50)

    @field_validator("task", "assigned_to_name", "deadline", mode="before")
    @classmethod
    def _strip_optional_values(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        cleaned = value.strip()
        return cleaned or None


class MeetingExportResponse(BaseModel):
    format: str
    filename: str
    content: str


class AskAcrossMeetingsRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=6, ge=1, le=20)

    @field_validator("question", mode="before")
    @classmethod
    def _strip_question(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return value.strip()


class AskCitation(BaseModel):
    meeting_id: uuid.UUID
    meeting_title: str
    transcript_id: uuid.UUID
    chunk_index: int
    score: float
    snippet: str


class AskAcrossMeetingsResponse(BaseModel):
    answer: str
    citations: list[AskCitation] = Field(default_factory=list)
