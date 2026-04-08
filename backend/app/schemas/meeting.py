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


class TranscriptBrief(BaseModel):
    id: uuid.UUID
    content: str
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
