"""Tests for the Groq-backed translation service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.core.config import settings
from app.models.meeting import Meeting
from app.models.participant import Participant
from app.models.transcript import Transcript
from app.services.translation_service import (
    TranscriptAccessDeniedError,
    TranscriptNotFoundError,
    TranslationError,
    TranslationService,
)


@pytest.mark.asyncio
async def test_missing_transcript_raises_not_found(db_session, sample_user) -> None:
    service = TranslationService(db_session)
    with pytest.raises(TranscriptNotFoundError):
        await service.translate(uuid.uuid4(), sample_user, "en")


@pytest.mark.asyncio
async def test_access_denied_for_non_participant(db_session, sample_user) -> None:
    from app.models.user import User

    other = User(
        id=uuid.uuid4(),
        email=f"other-{uuid.uuid4().hex[:6]}@meetai.test",
        hashed_password="x",
        full_name=None,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(other)
    now = datetime.now(timezone.utc)
    meeting = Meeting(id=uuid.uuid4(), title="Private", host_id=other.id, created_at=now)
    db_session.add(meeting)
    db_session.add(
        Participant(meeting_id=meeting.id, user_id=other.id, role="host", joined_at=now)
    )
    transcript = Transcript(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        content="Content",
        transcript_text="Content",
        created_at=now,
    )
    db_session.add(transcript)
    await db_session.commit()

    service = TranslationService(db_session)
    with pytest.raises(TranscriptAccessDeniedError):
        await service.translate(transcript.id, sample_user, "en")


@pytest.mark.asyncio
async def test_same_language_shortcut(db_session, sample_user) -> None:
    """When target == source language we persist the source text and skip Groq."""
    now = datetime.now(timezone.utc)
    meeting = Meeting(
        id=uuid.uuid4(), title="En meeting", host_id=sample_user.id, created_at=now
    )
    db_session.add(meeting)
    db_session.add(
        Participant(
            meeting_id=meeting.id, user_id=sample_user.id, role="host", joined_at=now
        )
    )
    transcript = Transcript(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        content="Hello world",
        transcript_text="Hello world",
        cleaned_transcript="Hello world",
        language="en",
        created_at=now,
    )
    db_session.add(transcript)
    await db_session.commit()

    service = TranslationService(db_session)
    result = await service.translate(transcript.id, sample_user, "EN")
    assert result.target_language == "en"
    assert result.text == "Hello world"


@pytest.mark.asyncio
async def test_missing_groq_key_raises_translation_error(
    db_session, sample_user, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "groq_api_key", "", raising=False)

    now = datetime.now(timezone.utc)
    meeting = Meeting(
        id=uuid.uuid4(), title="Cross-language", host_id=sample_user.id, created_at=now
    )
    db_session.add(meeting)
    db_session.add(
        Participant(
            meeting_id=meeting.id, user_id=sample_user.id, role="host", joined_at=now
        )
    )
    transcript = Transcript(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        content="Hola mundo",
        transcript_text="Hola mundo",
        cleaned_transcript="Hola mundo",
        language="es",
        created_at=now,
    )
    db_session.add(transcript)
    await db_session.commit()

    service = TranslationService(db_session)
    with pytest.raises(TranslationError):
        await service.translate(transcript.id, sample_user, "en")


@pytest.mark.asyncio
async def test_empty_target_raises(db_session, sample_user) -> None:
    service = TranslationService(db_session)
    with pytest.raises(TranslationError):
        await service.translate(uuid.uuid4(), sample_user, "   ")
