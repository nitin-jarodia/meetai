import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    hosted_meetings: Mapped[list["Meeting"]] = relationship(
        "Meeting", back_populates="host", foreign_keys="Meeting.host_id"
    )
    participations: Mapped[list["Participant"]] = relationship(
        "Participant", back_populates="user"
    )
    meeting_questions: Mapped[list["MeetingQAEntry"]] = relationship(
        "MeetingQAEntry", back_populates="user"
    )
    created_action_items: Mapped[list["MeetingActionItem"]] = relationship(
        "MeetingActionItem",
        back_populates="created_by",
        foreign_keys="MeetingActionItem.created_by_id",
    )
    assigned_action_items: Mapped[list["MeetingActionItem"]] = relationship(
        "MeetingActionItem",
        back_populates="assigned_user",
        foreign_keys="MeetingActionItem.assigned_user_id",
    )
    processing_jobs: Mapped[list["MeetingProcessingJob"]] = relationship(
        "MeetingProcessingJob", back_populates="created_by"
    )
