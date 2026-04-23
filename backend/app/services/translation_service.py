"""Translate a cleaned transcript via Groq chat completions."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass

from groq import Groq
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.transcript import Transcript
from app.models.user import User
from app.repositories.meeting_repository import MeetingRepository
from app.repositories.transcript_repository import TranscriptRepository


class TranslationError(Exception):
    """Raised when translation fails (missing key, API error, or empty result)."""


class TranscriptNotFoundError(Exception):
    """Raised when translating an unknown or inaccessible transcript."""


class TranscriptAccessDeniedError(Exception):
    """Raised when the caller is not a participant of the transcript's meeting."""


@dataclass(slots=True)
class TranslationResult:
    transcript_id: uuid.UUID
    target_language: str
    text: str


_LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "hi": "Hindi",
    "ar": "Arabic",
    "ru": "Russian",
    "tr": "Turkish",
    "id": "Indonesian",
    "vi": "Vietnamese",
}


def _language_name(code: str) -> str:
    return _LANGUAGE_NAMES.get(code.lower(), code)


class TranslationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.transcripts = TranscriptRepository(session)
        self.meetings = MeetingRepository(session)

    async def _get_transcript_for_user(
        self, transcript_id: uuid.UUID, user: User
    ) -> Transcript:
        transcript = await self.transcripts.get_by_id(transcript_id)
        if not transcript:
            raise TranscriptNotFoundError()
        meeting = await self.meetings.get_by_id(transcript.meeting_id)
        if not meeting:
            raise TranscriptNotFoundError()
        if meeting.host_id == user.id:
            return transcript
        if await self.meetings.get_participant(meeting.id, user.id):
            return transcript
        raise TranscriptAccessDeniedError()

    @staticmethod
    def _pick_source(transcript: Transcript) -> str:
        return (
            (transcript.cleaned_transcript or "").strip()
            or (transcript.transcript_text or "").strip()
            or (transcript.content or "").strip()
        )

    async def translate(
        self, transcript_id: uuid.UUID, user: User, target: str
    ) -> TranslationResult:
        target_code = target.strip().lower()
        if not target_code:
            raise TranslationError("Target language is required")

        transcript = await self._get_transcript_for_user(transcript_id, user)
        source_text = self._pick_source(transcript)
        if not source_text:
            raise TranslationError("Transcript has no content to translate")

        if (transcript.language or "").lower() == target_code:
            transcript.translated_text = source_text
            transcript.translated_language = target_code
            await self.transcripts.save(transcript)
            return TranslationResult(
                transcript_id=transcript.id,
                target_language=target_code,
                text=source_text,
            )

        translated_text = await asyncio.to_thread(
            _translate_with_groq, source_text, target_code
        )
        transcript.translated_text = translated_text
        transcript.translated_language = target_code
        await self.transcripts.save(transcript)
        return TranslationResult(
            transcript_id=transcript.id,
            target_language=target_code,
            text=translated_text,
        )


def _translate_with_groq(text: str, target_code: str) -> str:
    if not settings.groq_api_key:
        raise TranslationError(
            "Translation requires GROQ_API_KEY. Set it in backend/.env and retry."
        )

    client = Groq(api_key=settings.groq_api_key)
    target_name = _language_name(target_code)

    # Chunk long transcripts so we stay well within Groq's context window.
    max_chars_per_request = 9000
    if len(text) <= max_chars_per_request:
        pieces = [text]
    else:
        pieces = _split_into_chunks(text, max_chars_per_request)

    translated_parts: list[str] = []
    for piece in pieces:
        try:
            chat = client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You translate meeting transcripts into {target_name} "
                            f"({target_code}). Preserve meaning, structure, and "
                            "speaker labels. Do not summarize. Return only the "
                            "translated text."
                        ),
                    },
                    {
                        "role": "user",
                        "content": piece,
                    },
                ],
                temperature=0.1,
                max_tokens=3500,
            )
        except Exception as exc:
            raise TranslationError(f"Groq API request failed: {exc}") from exc
        content = (chat.choices[0].message.content or "").strip()
        if not content:
            raise TranslationError("Groq returned an empty translation")
        translated_parts.append(content)
    return "\n\n".join(translated_parts).strip()


def _split_into_chunks(text: str, max_chars: int) -> list[str]:
    paragraphs = text.split("\n\n")
    out: list[str] = []
    current = ""
    for para in paragraphs:
        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) > max_chars and current:
            out.append(current)
            current = para
        else:
            current = candidate
    if current:
        out.append(current)
    return out
