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
    task: str
    assigned_to: str | None = None
    deadline: str | None = None


class TranscriptBrief(BaseModel):
    id: uuid.UUID
    transcript_text: str
    cleaned_transcript: str | None = None
    summary: str | None = None
    key_points: list[str] = Field(default_factory=list)
    action_items: list[ActionItemOut] = Field(default_factory=list)
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


class AudioUploadResponse(BaseModel):
    transcript: str
    cleaned_transcript: str
    summary: str
    key_points: list[str] = Field(default_factory=list)
    action_items: list[ActionItemOut] = Field(default_factory=list)


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
