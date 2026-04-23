import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, Uuid
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
    # Embeddings are stored as JSON for dialect portability. On Postgres we ALSO keep a
    # `vector` column via schema_patches for fast pgvector similarity queries.
    embedding: Mapped[list[float]] = mapped_column(JSON, nullable=False, default=list)
    embedding_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="search_chunks")
    transcript: Mapped["Transcript"] = relationship(
        "Transcript", back_populates="search_chunks"
    )
