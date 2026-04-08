from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.models.user import User
from app.services.ai_service import AIService, SummaryGenerationError, get_ai_service

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
