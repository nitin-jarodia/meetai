"""SQLAlchemy models — import all for metadata registration."""

from app.models.meeting import Meeting
from app.models.meeting_action_item import MeetingActionItem
from app.models.meeting_qa import MeetingQAEntry
from app.models.notification_preference import NotificationPreference
from app.models.participant import Participant
from app.models.processing_job import MeetingProcessingJob
from app.models.search_chunk import MeetingSearchChunk
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User

__all__ = [
    "User",
    "Meeting",
    "Participant",
    "Transcript",
    "TranscriptSegment",
    "MeetingQAEntry",
    "MeetingActionItem",
    "MeetingProcessingJob",
    "MeetingSearchChunk",
    "NotificationPreference",
]
