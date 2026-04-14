import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MeetingActionItem(Base):
    __tablename__ = "meeting_action_items"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("meetings.id"), nullable=False, index=True
    )
    transcript_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("transcripts.id"), nullable=True, index=True
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    task: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_to_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deadline: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open")
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="ai")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="action_items")
    transcript: Mapped["Transcript | None"] = relationship(
        "Transcript", back_populates="action_items_records"
    )
    created_by: Mapped["User | None"] = relationship(
        "User", back_populates="created_action_items", foreign_keys=[created_by_id]
    )
    assigned_user: Mapped["User | None"] = relationship(
        "User", back_populates="assigned_action_items", foreign_keys=[assigned_user_id]
    )
