import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MeetingQAEntry(Base):
    __tablename__ = "meeting_qa_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("meetings.id"), nullable=False, index=True
    )
    transcript_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("transcripts.id"), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="qa_entries")
    transcript: Mapped["Transcript | None"] = relationship(
        "Transcript", back_populates="qa_entries"
    )
    user: Mapped["User"] = relationship("User", back_populates="meeting_questions")
