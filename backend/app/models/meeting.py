import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.meeting_action_item import MeetingActionItem
from app.models.meeting_qa import MeetingQAEntry
from app.models.processing_job import MeetingProcessingJob
from app.models.search_chunk import MeetingSearchChunk
from app.models.transcript import Transcript


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    host: Mapped["User"] = relationship("User", back_populates="hosted_meetings")
    participants: Mapped[list["Participant"]] = relationship(
        "Participant", back_populates="meeting", cascade="all, delete-orphan"
    )
    transcripts: Mapped[list[Transcript]] = relationship(
        Transcript,
        back_populates="meeting",
        cascade="all, delete-orphan",
        order_by=Transcript.created_at.desc(),
    )
    qa_entries: Mapped[list[MeetingQAEntry]] = relationship(
        MeetingQAEntry,
        back_populates="meeting",
        cascade="all, delete-orphan",
        order_by=MeetingQAEntry.created_at.desc(),
    )
    action_items: Mapped[list[MeetingActionItem]] = relationship(
        MeetingActionItem,
        back_populates="meeting",
        cascade="all, delete-orphan",
        order_by=MeetingActionItem.created_at.desc(),
    )
    processing_jobs: Mapped[list[MeetingProcessingJob]] = relationship(
        MeetingProcessingJob,
        back_populates="meeting",
        cascade="all, delete-orphan",
        order_by=MeetingProcessingJob.created_at.desc(),
    )
    search_chunks: Mapped[list[MeetingSearchChunk]] = relationship(
        MeetingSearchChunk,
        back_populates="meeting",
        cascade="all, delete-orphan",
        order_by=MeetingSearchChunk.chunk_index.asc(),
    )
