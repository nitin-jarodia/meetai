import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.meeting import (
    AskAcrossMeetingsRequest,
    AskAcrossMeetingsResponse,
    AskCitation,
)
from app.services.ai_service import (
    AIService,
    QuestionAnsweringError,
    SummaryGenerationError,
    get_ai_service,
)
from app.services.search_service import SearchService

router = APIRouter(prefix="/ai", tags=["ai"])


class SummaryBody(BaseModel):
    text: str = Field(min_length=1, max_length=50000)


@router.post("/summary")
async def summarize_text(
    body: SummaryBody,
    ai: AIService = Depends(get_ai_service),
    _: User = Depends(get_current_user),
):
    """Optional endpoint to verify Groq integration."""
    try:
        summary = ai.generate_summary(body.text)
    except SummaryGenerationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    return {"summary": summary}


@router.post("/ask", response_model=AskAcrossMeetingsResponse)
async def ask_across_meetings(
    body: AskAcrossMeetingsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ai: AIService = Depends(get_ai_service),
):
    """Cross-meeting RAG: retrieve the top chunks, then let Groq answer with citations."""
    search = SearchService(db)
    passages = await search.retrieve_passages(
        current_user, body.question, top_k=body.top_k
    )
    if not passages:
        return AskAcrossMeetingsResponse(
            answer=(
                "I couldn't find anything relevant in your meetings yet. "
                "Try uploading a meeting transcript first."
            ),
            citations=[],
        )

    context_lines: list[str] = []
    citations: list[AskCitation] = []
    for idx, passage in enumerate(passages, start=1):
        tag = f"[{idx}]"
        context_lines.append(
            f"{tag} Meeting: {passage.meeting_title}\n{passage.content}"
        )
        citations.append(
            AskCitation(
                meeting_id=passage.meeting_id,
                meeting_title=passage.meeting_title,
                transcript_id=passage.transcript_id,
                chunk_index=passage.chunk_index,
                score=passage.score,
                snippet=passage.content[:280],
            )
        )

    context = "\n\n".join(context_lines)
    prompt = (
        "You answer questions using ONLY the meeting context below.\n"
        "Cite sources inline using [1], [2], etc. matching the provided snippets.\n"
        "If the answer is not present, say 'Not mentioned in your meetings.'\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {body.question}\n"
    )
    try:
        answer = await asyncio.to_thread(
            ai.answer_question, context, body.question
        )
        # Re-run with context-preserving instructions for citation formatting if the
        # provider simply returned the raw answer. Groq already handles this well
        # via the normal prompt path, so a fallback call is only used when empty.
        if not answer.strip():
            raise QuestionAnsweringError("Empty response")
    except QuestionAnsweringError:
        # Local fallback: answer using the combined context via the AI service.
        answer = ai.fallback_answer(context, body.question) or (
            "Not mentioned in your meetings."
        )

    return AskAcrossMeetingsResponse(answer=answer.strip(), citations=citations)
