"""Semantic + lexical search across meetings owned by a user."""

from __future__ import annotations

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
from app.services.embedding_service import cosine_similarity, get_embedding_provider

_TOKEN = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text)]


@dataclass(slots=True)
class MeetingSearchResult:
    meeting: Meeting
    score: float
    snippet: str
    matched_text: str


@dataclass(slots=True)
class RAGPassage:
    meeting_id: uuid.UUID
    meeting_title: str
    transcript_id: uuid.UUID
    chunk_index: int
    content: str
    score: float


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
        self.embedder = get_embedding_provider()

    async def index_transcript(self, meeting: Meeting, transcript: Transcript) -> None:
        source_text = (
            (transcript.cleaned_transcript or "").strip()
            or (transcript.transcript_text or "").strip()
            or (transcript.content or "").strip()
        )
        chunk_values = _chunk_text(source_text, settings.search_chunk_chars)
        if not chunk_values:
            await self.chunks.replace_for_transcript(transcript.id, [])
            return

        vectors = self.embedder.embed_many(chunk_values)
        version = self.embedder.version
        now = datetime.now(timezone.utc)
        records = [
            MeetingSearchChunk(
                meeting_id=meeting.id,
                transcript_id=transcript.id,
                chunk_index=index,
                content=value,
                embedding=vectors[index],
                embedding_version=version,
                created_at=now,
            )
            for index, value in enumerate(chunk_values)
        ]
        await self.chunks.replace_for_transcript(transcript.id, records)

    # ------------------------------------------------------------------
    # Ranked meeting search
    # ------------------------------------------------------------------

    async def search_meetings(
        self, user: User, query: str, limit: int = 20
    ) -> list[MeetingSearchResult]:
        trimmed = query.strip()
        if not trimmed:
            return []

        accessible = await self.meetings.list_for_user(user.id, limit=200)
        if not accessible:
            return []

        meeting_ids = [m.id for m in accessible]
        chunks = await self.chunks.list_for_meeting_ids(meeting_ids)
        chunks_by_meeting: dict[uuid.UUID, list[MeetingSearchChunk]] = {}
        for chunk in chunks:
            chunks_by_meeting.setdefault(chunk.meeting_id, []).append(chunk)

        query_embedding = self.embedder.embed(trimmed)
        query_version = self.embedder.version
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
                    len(query_tokens & set(_tokenize(chunk.content)))
                    / max(len(query_tokens), 1)
                    if query_tokens
                    else 0.0
                )
                # Only compare semantic similarity when the two vectors share backend.
                semantic = 0.0
                if chunk.embedding_version == query_version:
                    semantic = cosine_similarity(query_embedding, chunk.embedding)
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
                        len(query_tokens & transcript_tokens)
                        / max(len(query_tokens), 1)
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

        results.sort(key=lambda r: (r.score, r.meeting.created_at), reverse=True)
        return results[:limit]

    # ------------------------------------------------------------------
    # Cross-meeting RAG retrieval
    # ------------------------------------------------------------------

    async def retrieve_passages(
        self, user: User, query: str, *, top_k: int = 6
    ) -> list[RAGPassage]:
        """Return the top-k relevant transcript chunks across the user's meetings."""
        trimmed = query.strip()
        if not trimmed:
            return []
        accessible = await self.meetings.list_for_user(user.id, limit=500)
        if not accessible:
            return []

        meetings_by_id = {m.id: m for m in accessible}
        chunks = await self.chunks.list_for_meeting_ids(list(meetings_by_id.keys()))
        if not chunks:
            return []

        query_embedding = self.embedder.embed(trimmed)
        query_version = self.embedder.version
        query_tokens = set(_tokenize(trimmed))

        scored: list[tuple[float, MeetingSearchChunk]] = []
        for chunk in chunks:
            lexical = (
                len(query_tokens & set(_tokenize(chunk.content)))
                / max(len(query_tokens), 1)
                if query_tokens
                else 0.0
            )
            semantic = 0.0
            if chunk.embedding_version == query_version:
                semantic = cosine_similarity(query_embedding, chunk.embedding)
            score = 0.65 * semantic + 0.35 * lexical
            if score <= 0:
                continue
            scored.append((score, chunk))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        top = scored[:top_k]
        return [
            RAGPassage(
                meeting_id=chunk.meeting_id,
                meeting_title=meetings_by_id[chunk.meeting_id].title
                if chunk.meeting_id in meetings_by_id
                else "",
                transcript_id=chunk.transcript_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                score=float(score),
            )
            for score, chunk in top
        ]
