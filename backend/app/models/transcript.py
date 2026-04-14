import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("meetings.id"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    transcript_text: Mapped[str] = mapped_column(Text, nullable=False)
    cleaned_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_points: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    action_items: Mapped[list[dict[str, str | None]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    segment_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="transcripts")
    qa_entries: Mapped[list["MeetingQAEntry"]] = relationship(
        "MeetingQAEntry", back_populates="transcript"
    )
    action_items_records: Mapped[list["MeetingActionItem"]] = relationship(
        "MeetingActionItem", back_populates="transcript"
    )
    search_chunks: Mapped[list["MeetingSearchChunk"]] = relationship(
        "MeetingSearchChunk",
        back_populates="transcript",
        cascade="all, delete-orphan",
        order_by="MeetingSearchChunk.chunk_index.asc()",
    )
