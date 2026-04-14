from __future__ import annotations

import math
import re
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.meeting import Meeting
from app.models.search_chunk import MeetingSearchChunk
from app.models.transcript import Transcript
from app.models.user import User
from app.repositories.meeting_repository import MeetingRepository
from app.repositories.search_repository import SearchRepository

_TOKEN = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


@dataclass(slots=True)
class MeetingSearchResult:
    meeting: Meeting
    score: float
    snippet: str
    matched_text: str


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN.findall(text)]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


def _embed_text(text: str, dimensions: int) -> list[float]:
    counts = Counter(_tokenize(text))
    if not counts:
        return [0.0] * dimensions
    vector = [0.0] * dimensions
    for token, count in counts.items():
        index = hash(token) % dimensions
        sign = 1.0 if (hash(f"sign:{token}") % 2 == 0) else -1.0
        vector[index] += count * sign
    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [value / norm for value in vector]


def _chunk_text(text: str, chunk_chars: int) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    if len(normalized) <= chunk_chars:
        return [normalized]
    words = normalized.split(" ")
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for word in words:
        additional = len(word) + (1 if current else 0)
        if current and current_len + additional > chunk_chars:
            chunks.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += additional
    if current:
        chunks.append(" ".join(current))
    return chunks


class SearchService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.meetings = MeetingRepository(session)
        self.chunks = SearchRepository(session)

    async def index_transcript(self, meeting: Meeting, transcript: Transcript) -> None:
        source_text = (
            (transcript.cleaned_transcript or "").strip()
            or (transcript.transcript_text or "").strip()
            or (transcript.content or "").strip()
        )
        chunk_values = _chunk_text(source_text, settings.search_chunk_chars)
        now = datetime.now(timezone.utc)
        records = [
            MeetingSearchChunk(
                meeting_id=meeting.id,
                transcript_id=transcript.id,
                chunk_index=index,
                content=value,
                embedding=_embed_text(value, settings.search_embedding_dimensions),
                created_at=now,
            )
            for index, value in enumerate(chunk_values)
        ]
        await self.chunks.replace_for_transcript(transcript.id, records)

    async def search_meetings(
        self, user: User, query: str, limit: int = 20
    ) -> list[MeetingSearchResult]:
        trimmed = query.strip()
        if not trimmed:
            return []

        accessible = await self.meetings.list_for_user(user.id, limit=100)
        if not accessible:
            return []

        meeting_ids = [meeting.id for meeting in accessible]
        chunks = await self.chunks.list_for_meeting_ids(meeting_ids)
        chunks_by_meeting: dict[uuid.UUID, list[MeetingSearchChunk]] = {}
        for chunk in chunks:
            chunks_by_meeting.setdefault(chunk.meeting_id, []).append(chunk)

        query_embedding = _embed_text(trimmed, settings.search_embedding_dimensions)
        query_tokens = set(_tokenize(trimmed))
        results: list[MeetingSearchResult] = []

        for meeting in accessible:
            base_text = " ".join(
                filter(None, [meeting.title, meeting.description or ""])
            ).strip()
            base_tokens = set(_tokenize(base_text))
            title_score = (
                len(query_tokens & base_tokens) / max(len(query_tokens), 1)
                if query_tokens
                else 0.0
            )

            best_chunk = ""
            best_semantic = 0.0
            best_lexical = 0.0
            for chunk in chunks_by_meeting.get(meeting.id, []):
                lexical = (
                    len(query_tokens & set(_tokenize(chunk.content))) / max(len(query_tokens), 1)
                    if query_tokens
                    else 0.0
                )
                semantic = _cosine_similarity(query_embedding, chunk.embedding)
                if semantic + lexical > best_semantic + best_lexical:
                    best_chunk = chunk.content
                    best_semantic = semantic
                    best_lexical = lexical

            transcript_bonus = 0.0
            if not best_chunk:
                latest = meeting.transcripts[0] if meeting.transcripts else None
                if latest:
                    transcript_text = (
                        latest.cleaned_transcript
                        or latest.transcript_text
                        or latest.summary
                        or ""
                    )
                    transcript_tokens = set(_tokenize(transcript_text))
                    transcript_bonus = (
                        len(query_tokens & transcript_tokens) / max(len(query_tokens), 1)
                        if query_tokens
                        else 0.0
                    )
                    best_chunk = transcript_text[:280]

            score = title_score * 0.35 + best_lexical * 0.35 + best_semantic * 0.30
            score = max(score, transcript_bonus * 0.3 + score)
            if score <= 0:
                continue

            snippet = best_chunk[:280].strip()
            results.append(
                MeetingSearchResult(
                    meeting=meeting,
                    score=score,
                    snippet=snippet,
                    matched_text=best_chunk,
                )
            )

        results.sort(key=lambda item: (item.score, item.meeting.created_at), reverse=True)
        return results[:limit]
