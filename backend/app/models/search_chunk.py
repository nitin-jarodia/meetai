import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MeetingSearchChunk(Base):
    __tablename__ = "meeting_search_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("meetings.id"), nullable=False, index=True
    )
    transcript_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("transcripts.id"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="search_chunks")
    transcript: Mapped["Transcript"] = relationship(
        "Transcript", back_populates="search_chunks"
    )
