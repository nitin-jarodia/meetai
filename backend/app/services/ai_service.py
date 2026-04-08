"""LLM providers — Groq today, OpenAI-compatible swap later."""

from abc import ABC, abstractmethod

from groq import Groq

from app.core.config import settings


class SummaryGenerationError(Exception):
    """Raised when Groq is unavailable or returns an invalid summary."""


class LLMProvider(ABC):
    """Abstract provider for summary / chat-style calls."""

    @abstractmethod
    def generate_summary(self, text: str) -> str:
        """Return a short meeting summary for the given transcript text."""
        raise NotImplementedError


class GroqProvider(LLMProvider):
    def __init__(self, api_key: str, model: str | None = None):
        self._client = Groq(api_key=api_key) if api_key else None
        self._model = model or settings.groq_model

    def generate_summary(self, text: str) -> str:
        if not self._client:
            raise SummaryGenerationError(
                "GROQ_API_KEY is not set. Configure it to generate summaries."
            )
        if not text.strip():
            raise SummaryGenerationError("No text to summarize.")
        try:
            chat = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Summarize the following meeting transcript into key points "
                            "and action items:\n\n"
                            f"{text[:12000]}"
                        ),
                    },
                ],
                temperature=0.3,
                max_tokens=1024,
            )
        except Exception as e:
            raise SummaryGenerationError(f"Groq API request failed: {e}") from e
        choice = chat.choices[0].message.content
        if not (choice or "").strip():
            raise SummaryGenerationError("Groq returned an empty summary.")
        return choice or ""


class OpenAIProviderStub(LLMProvider):
    """Placeholder for future OpenAI or other compatible APIs."""

    def generate_summary(self, text: str) -> str:
        raise SummaryGenerationError(
            "OpenAI provider is not implemented; use Groq (set GROQ_API_KEY)."
        )


def build_default_provider() -> LLMProvider:
    if settings.groq_api_key:
        return GroqProvider(api_key=settings.groq_api_key)
    return GroqProvider(api_key="")


class AIService:
    """Facade for AI features — inject a provider in tests or future DI."""

    def __init__(self, provider: LLMProvider | None = None):
        self._provider = provider or build_default_provider()

    def generate_summary(self, text: str) -> str:
        return self._provider.generate_summary(text)


def get_ai_service() -> AIService:
    return AIService()
