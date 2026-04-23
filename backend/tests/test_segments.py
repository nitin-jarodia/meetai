"""Tests for TranscriptSegment persistence and retrieval."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from sqlalchemy import func, select

from app.models.meeting import Meeting
from app.models.participant import Participant
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.repositories.transcript_repository import TranscriptRepository


@pytest.mark.asyncio
async def test_replace_and_load_segments(db_session, sample_user) -> None:
    now = datetime.now(timezone.utc)
    meeting = Meeting(
        id=uuid.uuid4(),
        title="Diarization test",
        host_id=sample_user.id,
        created_at=now,
    )
    db_session.add(meeting)
    db_session.add(
        Participant(
            meeting_id=meeting.id,
            user_id=sample_user.id,
            role="host",
            joined_at=now,
        )
    )
    transcript = Transcript(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        content="Hello everyone. Welcome to the call.",
        transcript_text="Hello everyone. Welcome to the call.",
        created_at=now,
    )
    db_session.add(transcript)
    await db_session.commit()

    repo = TranscriptRepository(db_session)
    segments = [
        TranscriptSegment(
            id=uuid.uuid4(),
            transcript_id=transcript.id,
            order_index=0,
            start_ms=0,
            end_ms=2000,
            text="Hello everyone.",
            speaker_label="Speaker 1",
            confidence=0.95,
            created_at=now,
        ),
        TranscriptSegment(
            id=uuid.uuid4(),
            transcript_id=transcript.id,
            order_index=1,
            start_ms=2000,
            end_ms=4500,
            text="Welcome to the call.",
            speaker_label="Speaker 2",
            confidence=0.88,
            created_at=now,
        ),
    ]
    await repo.replace_segments(transcript.id, segments)
    await db_session.commit()

    loaded = await repo.get_with_segments(transcript.id)
    assert loaded is not None
    ordered = sorted(loaded.segments, key=lambda s: s.order_index)
    assert [s.text for s in ordered] == [
        "Hello everyone.",
        "Welcome to the call.",
    ]
    assert [s.speaker_label for s in ordered] == ["Speaker 1", "Speaker 2"]
    assert ordered[0].end_ms == 2000

    # Replacing segments should fully overwrite previous rows.
    await repo.replace_segments(
        transcript.id,
        [
            TranscriptSegment(
                id=uuid.uuid4(),
                transcript_id=transcript.id,
                order_index=0,
                start_ms=0,
                end_ms=1500,
                text="Hi team.",
                speaker_label="Speaker 1",
                confidence=None,
                created_at=now,
            )
        ],
    )
    await db_session.commit()

    count_result = await db_session.execute(
        select(func.count())
        .select_from(TranscriptSegment)
        .where(TranscriptSegment.transcript_id == transcript.id)
    )
    assert count_result.scalar_one() == 1

    only_result = await db_session.execute(
        select(TranscriptSegment).where(
            TranscriptSegment.transcript_id == transcript.id
        )
    )
    only_segment = only_result.scalars().one()
    assert only_segment.text == "Hi team."
