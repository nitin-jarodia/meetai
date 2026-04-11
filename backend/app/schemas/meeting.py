import uuid
from datetime import datetime

from pydantic import BaseModel, Field

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
    summary: str
    key_points: list[str] = Field(default_factory=list)
    action_items: list[ActionItemOut] = Field(default_factory=list)
