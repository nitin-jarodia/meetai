"""Meeting use cases."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.meeting_action_item import MeetingActionItem
from app.models.meeting_qa import MeetingQAEntry
from app.models.meeting import Meeting
from app.models.participant import Participant
from app.models.processing_job import MeetingProcessingJob
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User
from app.repositories.meeting_repository import MeetingRepository
from app.repositories.qa_repository import QARepository
from app.repositories.transcript_repository import TranscriptRepository
from app.schemas.meeting import (
    ActionItemOut,
    MeetingCreate,
    MeetingDetail,
    MeetingExportResponse,
    MeetingListResponse,
    MeetingProcessingJobOut,
    MeetingQAEntryOut,
    MeetingOut,
    ParticipantBrief,
    TranscriptBrief,
)
from app.schemas.user import UserOut
from app.services.action_item_service import sync_ai_action_items
from app.services.ai_service import (
    AIService,
    MeetingAnalysis,
    QuestionAnsweringError,
    SummaryGenerationError,
    TranscriptCleanupError,
)
from app.services.search_service import SearchService
from app.services.transcription_service import (
    TranscriptionError,
    TranscriptionResult,
    transcribe_audio,
)


class MeetingNotFoundError(Exception):
    """Raised when no meeting exists for the given id."""


class MeetingAccessDeniedError(Exception):
    """Raised when the user is not the host or a participant."""


class TranscriptNotFoundError(Exception):
    """Raised when no transcript exists for the meeting."""


@dataclass(slots=True)
class ProcessedAudioUpload:
    transcript_id: uuid.UUID
    transcript: str
    cleaned_transcript: str
    summary: str
    key_points: list[str]
    action_items: list[dict[str, str | None]]
    language: str | None
    duration_ms: int | None


@dataclass(slots=True)
class MeetingAnswer:
    answer: str
    entry: MeetingQAEntryOut


def serialize_action_item(item: MeetingActionItem) -> ActionItemOut:
    return ActionItemOut(
        id=item.id,
        task=item.task,
        assigned_to=item.assigned_to_name,
        deadline=item.deadline,
        due_at=item.due_at,
        status=item.status,
        assigned_user_id=item.assigned_user_id,
        source=item.source,
        updated_at=item.updated_at,
    )


def serialize_transcript(transcript: Transcript) -> TranscriptBrief:
    action_items_payload = transcript.action_items or []
    return TranscriptBrief(
        id=transcript.id,
        transcript_text=transcript.transcript_text or transcript.content or "",
        cleaned_transcript=transcript.cleaned_transcript,
        translated_text=transcript.translated_text,
        translated_language=transcript.translated_language,
        summary=transcript.summary,
        key_points=transcript.key_points or [],
        action_items=[
            ActionItemOut(
                id=_safe_uuid(item.get("id")) if isinstance(item, dict) else None,
                task=(item.get("task") or "") if isinstance(item, dict) else "",
                assigned_to=item.get("assigned_to") if isinstance(item, dict) else None,
                deadline=item.get("deadline") if isinstance(item, dict) else None,
                due_at=_parse_iso(item.get("due_at")) if isinstance(item, dict) else None,
                status=item.get("status") if isinstance(item, dict) else None,
            )
            for item in action_items_payload
        ],
        language=transcript.language,
        duration_ms=transcript.duration_ms,
        audio_path=transcript.audio_path,
        has_audio=bool(transcript.audio_path),
        segment_index=transcript.segment_index,
        created_at=transcript.created_at,
    )


def _safe_uuid(value: object) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


def _parse_iso(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def serialize_job(job: MeetingProcessingJob) -> MeetingProcessingJobOut:
    return MeetingProcessingJobOut(
        id=job.id,
        meeting_id=job.meeting_id,
        filename=job.filename,
        status=job.status,
        stage=job.stage,
        progress=job.progress,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
        created_by=UserOut.model_validate(job.created_by),
    )


def serialize_qa_entry(entry: MeetingQAEntry) -> MeetingQAEntryOut:
    return MeetingQAEntryOut(
        id=entry.id,
        transcript_id=entry.transcript_id,
        question=entry.question,
        answer=entry.answer,
        created_at=entry.created_at,
        asked_by=UserOut.model_validate(entry.user),
    )


class MeetingService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.meetings = MeetingRepository(session)
        self.qa_entries = QARepository(session)
        self.transcripts = TranscriptRepository(session)

    def _serialize_meeting_detail(self, meeting: Meeting) -> MeetingDetail:
        host_out = UserOut.model_validate(meeting.host)
        participants = [
            ParticipantBrief(
                user_id=participant.user_id,
                role=participant.role,
                joined_at=participant.joined_at,
                user=UserOut.model_validate(participant.user),
            )
            for participant in meeting.participants
        ]
        transcripts = [serialize_transcript(t) for t in meeting.transcripts]
        return MeetingDetail(
            id=meeting.id,
            title=meeting.title,
            description=meeting.description,
            host_id=meeting.host_id,
            created_at=meeting.created_at,
            host=host_out,
            participants=participants,
            transcripts=transcripts,
            qa_history=[serialize_qa_entry(entry) for entry in meeting.qa_entries],
            action_items=[serialize_action_item(item) for item in meeting.action_items],
            processing_jobs=[serialize_job(job) for job in meeting.processing_jobs],
        )

    async def create_meeting(self, host: User, data: MeetingCreate) -> MeetingOut:
        now = datetime.now(timezone.utc)
        meeting = Meeting(
            title=data.title,
            description=data.description,
            host_id=host.id,
            created_at=now,
        )
        await self.meetings.create(meeting)
        await self.meetings.add_participant(
            Participant(
                meeting_id=meeting.id,
                user_id=host.id,
                role="host",
                joined_at=now,
            )
        )
        return MeetingOut.model_validate(meeting)

    async def join_meeting(self, meeting_id: uuid.UUID, user: User) -> MeetingOut:
        meeting = await self.meetings.get_by_id(meeting_id)
        if not meeting:
            raise ValueError("Meeting not found")
        existing = await self.meetings.get_participant(meeting_id, user.id)
        if existing:
            return MeetingOut.model_validate(meeting)
        await self.meetings.add_participant(
            Participant(
                meeting_id=meeting.id,
                user_id=user.id,
                role="member",
                joined_at=datetime.now(timezone.utc),
            )
        )
        meeting = await self.meetings.get_by_id(meeting_id)
        assert meeting is not None
        return MeetingOut.model_validate(meeting)

    async def list_meetings(
        self, user: User, query: str | None = None, limit: int = 50
    ) -> MeetingListResponse:
        meetings = await self.meetings.list_for_user(user.id, query=query, limit=limit)
        return MeetingListResponse(
            items=[self._serialize_meeting_detail(meeting) for meeting in meetings]
        )

    async def get_meeting_detail(
        self, meeting_id: uuid.UUID, user: User
    ) -> MeetingDetail | None:
        meeting = await self._get_meeting_for_user(meeting_id, user)
        return self._serialize_meeting_detail(meeting)

    async def _get_meeting_for_user(self, meeting_id: uuid.UUID, user: User) -> Meeting:
        meeting = await self.meetings.get_by_id(meeting_id)
        if not meeting:
            raise MeetingNotFoundError()
        if meeting.host_id == user.id:
            return meeting
        if await self.meetings.get_participant(meeting_id, user.id):
            return meeting
        raise MeetingAccessDeniedError()

    async def _analyze_transcript(
        self, transcript_text: str, ai: AIService
    ) -> MeetingAnalysis:
        try:
            return await asyncio.to_thread(ai.generate_analysis, transcript_text)
        except SummaryGenerationError:
            return ai.fallback_analysis(transcript_text)

    async def _clean_transcript(self, transcript_text: str, ai: AIService) -> str:
        try:
            return await asyncio.to_thread(ai.clean_transcript, transcript_text)
        except TranscriptCleanupError:
            return ai.fallback_clean_transcript(transcript_text)

    @staticmethod
    def _select_transcript_source(transcript: Transcript) -> str:
        return (
            (transcript.cleaned_transcript or "").strip()
            or (transcript.transcript_text or "").strip()
            or (transcript.content or "").strip()
        )

    async def process_audio_upload(
        self,
        meeting_id: uuid.UUID,
        user: User,
        saved_file_path: Path,
        ai: AIService,
        *,
        persistent_audio_path: Path | None = None,
        audio_mime_type: str | None = None,
        progress_callback: Callable[[str, float], Awaitable[None]] | None = None,
    ) -> ProcessedAudioUpload:
        """
        Transcribe audio, generate structured analysis, persist Transcript +
        timestamped segments, and return the structured API payload.

        If ``persistent_audio_path`` is provided, it is stored relative to the
        backend's uploads directory on the Transcript so the frontend can stream
        it back for click-to-seek playback.
        """
        meeting = await self._get_meeting_for_user(meeting_id, user)
        if progress_callback:
            await progress_callback("transcribing", 0.2)

        transcription: TranscriptionResult = await asyncio.to_thread(
            transcribe_audio, str(saved_file_path)
        )
        transcript_text = transcription.text

        if progress_callback:
            await progress_callback("cleaning_transcript", 0.5)
        cleaned_transcript = await self._clean_transcript(transcript_text, ai)
        if progress_callback:
            await progress_callback("analyzing_transcript", 0.75)
        analysis = await self._analyze_transcript(cleaned_transcript, ai)

        audio_rel_path: str | None = None
        if persistent_audio_path is not None:
            try:
                audio_rel_path = str(
                    persistent_audio_path.resolve().relative_to(
                        settings.backend_root.resolve()
                    )
                )
            except ValueError:
                audio_rel_path = str(persistent_audio_path.resolve())

        now = datetime.now(timezone.utc)
        transcript = await self.meetings.add_transcript(
            Transcript(
                meeting_id=meeting.id,
                content=transcript_text,
                transcript_text=transcript_text,
                cleaned_transcript=cleaned_transcript,
                summary=analysis.summary,
                key_points=analysis.key_points,
                action_items=[item.model_dump() for item in analysis.action_items],
                language=transcription.language,
                duration_ms=transcription.duration_ms or None,
                audio_path=audio_rel_path,
                audio_mime_type=audio_mime_type,
                segment_index=None,
                created_at=now,
            )
        )

        # Persist timestamped + diarized segments
        segment_rows = [
            TranscriptSegment(
                transcript_id=transcript.id,
                order_index=seg.order_index,
                start_ms=seg.start_ms,
                end_ms=seg.end_ms,
                text=seg.text,
                speaker_label=seg.speaker_label,
                confidence=seg.confidence,
                created_at=now,
            )
            for seg in transcription.segments
        ]
        await self.transcripts.replace_segments(transcript.id, segment_rows)

        await sync_ai_action_items(
            self.session, meeting, transcript, analysis.action_items
        )
        if progress_callback:
            await progress_callback("indexing_search", 0.9)
        await SearchService(self.session).index_transcript(meeting, transcript)
        return ProcessedAudioUpload(
            transcript_id=transcript.id,
            transcript=transcript_text,
            cleaned_transcript=cleaned_transcript,
            summary=analysis.summary,
            key_points=analysis.key_points,
            action_items=transcript.action_items,
            language=transcription.language,
            duration_ms=transcription.duration_ms or None,
        )

    async def ask_meeting_question(
        self,
        meeting_id: uuid.UUID,
        user: User,
        question: str,
        ai: AIService,
    ) -> MeetingAnswer:
        meeting = await self._get_meeting_for_user(meeting_id, user)
        transcript = await self.meetings.get_latest_transcript(meeting.id)
        if not transcript:
            raise TranscriptNotFoundError()

        transcript_source = self._select_transcript_source(transcript)
        if not transcript_source:
            raise TranscriptNotFoundError()

        try:
            answer = await asyncio.to_thread(
                ai.answer_question,
                transcript_source,
                question.strip(),
            )
        except QuestionAnsweringError:
            answer = ai.fallback_answer(transcript_source, question.strip())

        now = datetime.now(timezone.utc)
        entry = await self.qa_entries.create(
            MeetingQAEntry(
                meeting_id=meeting.id,
                transcript_id=transcript.id,
                user_id=user.id,
                question=question.strip(),
                answer=answer,
                created_at=now,
            )
        )
        entry.user = user
        return MeetingAnswer(answer=answer, entry=serialize_qa_entry(entry))

    async def export_meeting(
        self, meeting_id: uuid.UUID, user: User, export_format: str
    ) -> MeetingExportResponse:
        meeting = await self._get_meeting_for_user(meeting_id, user)
        detail = self._serialize_meeting_detail(meeting)
        if export_format == "json":
            return MeetingExportResponse(
                format="json",
                filename=f"{meeting.title[:40].strip() or 'meeting'}-notes.json",
                content=detail.model_dump_json(indent=2),
            )

        latest_transcript = detail.transcripts[0] if detail.transcripts else None
        key_points = (
            "\n".join(f"- {point}" for point in latest_transcript.key_points)
            if latest_transcript
            else ""
        )
        action_items = "\n".join(
            f"- [{item.status or 'open'}] {item.task}"
            + (f" (owner: {item.assigned_to})" if item.assigned_to else "")
            + (f" (deadline: {item.deadline})" if item.deadline else "")
            for item in detail.action_items
        )
        qa_history = "\n\n".join(
            f"Q: {entry.question}\nA: {entry.answer}" for entry in detail.qa_history
        )
        transcript_text = (
            latest_transcript.cleaned_transcript
            or latest_transcript.transcript_text
            if latest_transcript
            else ""
        )
        content = "\n".join(
            [
                f"# {detail.title}",
                "",
                f"Created: {detail.created_at.isoformat()}",
                f"Host: {detail.host.email}",
                "",
                "## Summary",
                latest_transcript.summary
                if latest_transcript and latest_transcript.summary
                else "No summary available.",
                "",
                "## Key Points",
                key_points or "- None yet",
                "",
                "## Action Items",
                action_items or "- None yet",
                "",
                "## Q&A",
                qa_history or "No Q&A yet.",
                "",
                "## Transcript",
                transcript_text or "No transcript available.",
            ]
        )
        return MeetingExportResponse(
            format="markdown",
            filename=f"{meeting.title[:40].strip() or 'meeting'}-notes.md",
            content=content,
        )
