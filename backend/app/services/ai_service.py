"""LLM providers — Groq today, OpenAI-compatible swap later."""

from __future__ import annotations

import json
import math
import re
from abc import ABC, abstractmethod
from collections import Counter

from groq import Groq
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.config import settings


class SummaryGenerationError(Exception):
    """Raised when Groq is unavailable or returns an invalid summary."""


class QuestionAnsweringError(Exception):
    """Raised when the LLM cannot answer a transcript question."""


class TranscriptCleanupError(Exception):
    """Raised when the LLM cannot clean a transcript."""


class ActionItem(BaseModel):
    task: str = Field(min_length=1)
    assigned_to: str | None = None
    deadline: str | None = None

    @field_validator("task", "assigned_to", "deadline", mode="before")
    @classmethod
    def _strip_optional_text(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        cleaned = value.strip()
        return cleaned or None


class MeetingAnalysis(BaseModel):
    summary: str = Field(min_length=1)
    key_points: list[str] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)

    @field_validator("summary", mode="before")
    @classmethod
    def _strip_summary(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return value.strip()

    @field_validator("key_points", mode="after")
    @classmethod
    def _clean_key_points(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]


_SENT_END = re.compile(r"(?<=[。！？!?\.])\s*")
_TOKEN = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)
_QA_MAX_CHARS = 5000
_ACTION_HINT = re.compile(
    r"\b(action item|todo|follow up|follow-up|next step|need to|needs to|"
    r"should|will|owner|deadline|by\s+\w+|before\s+\w+|tomorrow|next\s+\w+)\b",
    re.IGNORECASE,
)
_OWNER_HINT = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:will|should|needs to|is going to)\b"
)
_DEADLINE_HINT = re.compile(
    r"\b(by\s+[^,.;]+|before\s+[^,.;]+|tomorrow|next\s+\w+|this\s+\w+)\b",
    re.IGNORECASE,
)


def _split_sentences(text: str) -> list[str]:
    """Split on CJK/Latin sentence boundaries; fallback to whole text."""
    text = " ".join(text.split())
    if not text:
        return []
    parts = [p.strip() for p in _SENT_END.split(text) if p.strip()]
    if len(parts) <= 1 and text:
        return [text]
    return parts


def _local_fallback_summary(text: str, *, max_sentences: int = 7) -> str:
    """
    Extractive summary when no LLM is configured (no API key).
    Picks informative sentences by within-document token frequency — works offline.
    """
    sents = _split_sentences(text)
    if not sents:
        return ""

    if len(sents) == 1:
        body = sents[0]
        return (
            "Summary (offline — set GROQ_API_KEY for an AI-written summary):\n\n"
            f"{body}"
        )

    all_tokens: list[str] = []
    per_sent: list[list[str]] = []
    for s in sents:
        tok = [t.lower() for t in _TOKEN.findall(s)]
        per_sent.append(tok)
        all_tokens.extend(tok)

    freq = Counter(all_tokens)

    def score(i: int) -> float:
        tok = per_sent[i]
        if not tok:
            return 0.0
        # Slightly favor early sentences (titles/setups)
        position = 1.0 / (1.0 + 0.15 * i)
        density = sum(1.0 / (1.0 + math.log(1 + freq[w])) for w in tok) / len(tok)
        return density * position

    order_by_score = sorted(range(len(sents)), key=lambda i: score(i), reverse=True)
    pick = min(max_sentences, max(3, len(sents) // 2 + 1))
    top_idx = set(order_by_score[:pick])
    chosen = [sents[i] for i in range(len(sents)) if i in top_idx]

    lines = "\n".join(f"• {s}" for s in chosen)
    return (
        "Summary (offline extractive — set GROQ_API_KEY for an AI-written summary):\n\n"
        f"{lines}"
    )


def _top_sentences(text: str, *, limit: int = 4) -> list[str]:
    sents = _split_sentences(text)
    if not sents:
        return []

    all_tokens: list[str] = []
    per_sent: list[list[str]] = []
    for sent in sents:
        tokens = [token.lower() for token in _TOKEN.findall(sent)]
        per_sent.append(tokens)
        all_tokens.extend(tokens)

    freq = Counter(all_tokens)

    def score(i: int) -> float:
        tokens = per_sent[i]
        if not tokens:
            return 0.0
        position = 1.0 / (1.0 + 0.15 * i)
        density = sum(1.0 / (1.0 + math.log(1 + freq[word])) for word in tokens) / len(
            tokens
        )
        return density * position

    ranked = sorted(range(len(sents)), key=score, reverse=True)
    chosen = sorted(ranked[:limit])
    return [sents[index] for index in chosen if sents[index].strip()]


def _local_fallback_key_points(text: str, *, limit: int = 4) -> list[str]:
    points: list[str] = []
    seen: set[str] = set()
    for sentence in _top_sentences(text, limit=limit + 2):
        cleaned = sentence.strip("•- \n\t")
        normalized = cleaned.lower()
        if len(cleaned) < 20 or normalized in seen:
            continue
        seen.add(normalized)
        points.append(cleaned)
        if len(points) >= limit:
            break
    return points


def _local_fallback_action_items(text: str, *, limit: int = 5) -> list[ActionItem]:
    actions: list[ActionItem] = []
    seen: set[str] = set()
    for sentence in _split_sentences(text):
        cleaned = sentence.strip("•- \n\t")
        lowered = cleaned.lower()
        if len(cleaned) < 12 or lowered in seen:
            continue
        if not _ACTION_HINT.search(cleaned):
            continue

        owner_match = _OWNER_HINT.search(cleaned)
        deadline_match = _DEADLINE_HINT.search(cleaned)
        actions.append(
            ActionItem(
                task=cleaned,
                assigned_to=owner_match.group(1) if owner_match else None,
                deadline=deadline_match.group(1) if deadline_match else None,
            )
        )
        seen.add(lowered)
        if len(actions) >= limit:
            break
    return actions


def _local_fallback_answer(transcript: str, question: str) -> str:
    question_tokens = {token.lower() for token in _TOKEN.findall(question) if len(token) > 2}
    if not question_tokens:
        return "Not mentioned in the meeting"

    best_sentence = ""
    best_score = 0.0
    for sentence in _split_sentences(transcript):
        sentence_tokens = {token.lower() for token in _TOKEN.findall(sentence)}
        if not sentence_tokens:
            continue
        overlap = len(question_tokens & sentence_tokens)
        if overlap <= 0:
            continue
        score = overlap / max(len(question_tokens), 1)
        if any(char.isdigit() for char in question) and any(char.isdigit() for char in sentence):
            score += 0.2
        if score > best_score:
            best_score = score
            best_sentence = sentence.strip()

    if not best_sentence:
        return "Not mentioned in the meeting"
    return best_sentence


def _local_fallback_analysis(text: str) -> MeetingAnalysis:
    return MeetingAnalysis(
        summary=_local_fallback_summary(text),
        key_points=_local_fallback_key_points(text),
        action_items=_local_fallback_action_items(text),
    )


def _extract_json_payload(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise SummaryGenerationError("Groq returned invalid JSON.")
    return text[start : end + 1]


def _parse_analysis_response(raw_text: str) -> MeetingAnalysis:
    try:
        payload = json.loads(_extract_json_payload(raw_text))
    except json.JSONDecodeError as e:
        raise SummaryGenerationError("Groq returned invalid JSON.") from e

    try:
        return MeetingAnalysis.model_validate(payload)
    except ValidationError as e:
        raise SummaryGenerationError("Groq returned an invalid JSON structure.") from e


class LLMProvider(ABC):
    """Abstract provider for structured meeting analysis."""

    @abstractmethod
    def generate_analysis(self, text: str) -> MeetingAnalysis:
        """Return structured meeting analysis for the given transcript text."""
        raise NotImplementedError

    def generate_summary(self, text: str) -> str:
        return self.generate_analysis(text).summary

    @abstractmethod
    def clean_transcript(self, text: str) -> str:
        """Return a cleaned transcript that preserves meaning."""
        raise NotImplementedError

    @abstractmethod
    def answer_question(self, transcript: str, question: str) -> str:
        """Answer a question using only transcript content."""
        raise NotImplementedError


class GroqProvider(LLMProvider):
    def __init__(self, api_key: str, model: str | None = None):
        self._client = Groq(api_key=api_key) if api_key else None
        self._model = model or settings.groq_model

    def generate_analysis(self, text: str) -> MeetingAnalysis:
        if not text.strip():
            raise SummaryGenerationError("No text to summarize.")
        if not self._client:
            return _local_fallback_analysis(text)
        try:
            chat = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You analyze meeting transcripts and return only valid JSON. "
                            'Use exactly this structure: {"summary":"...","key_points":["..."],'
                            '"action_items":[{"task":"...","assigned_to":"...","deadline":null}]}. '
                            "Use only facts explicitly present in the provided transcript. "
                            "Use exact names, owners, and deadline wording from the transcript. "
                            "If the transcript was edited, trust the edited transcript over any "
                            "earlier version. Keep summary, key points, and action items "
                            "internally consistent with each other and with the transcript. "
                            "Only include action items that are clearly actionable. "
                            "Use null when an assignee or deadline is unknown. "
                            "Do not include markdown, code fences, or extra commentary."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "Analyze the following meeting transcript and produce the JSON "
                            "structure exactly as requested.\n\n"
                            "Important rules:\n"
                            "- Do not reuse names from previous transcript versions.\n"
                            "- If an owner name appears in the transcript, copy it exactly.\n"
                            "- If no owner is stated for a task, assigned_to must be null.\n"
                            "- If no deadline is stated for a task, deadline must be null.\n\n"
                            f"{text[:12000]}"
                        ),
                    },
                ],
                temperature=0.1,
                max_tokens=1200,
            )
        except Exception as e:
            raise SummaryGenerationError(f"Groq API request failed: {e}") from e
        choice = chat.choices[0].message.content
        if not (choice or "").strip():
            raise SummaryGenerationError("Groq returned an empty summary.")
        return _parse_analysis_response(choice or "")

    def clean_transcript(self, text: str) -> str:
        if not text.strip():
            raise TranscriptCleanupError("No transcript text to clean.")
        if not self._client:
            return text

        prompt = (
            "You are an AI assistant.\n\n"
            "Clean the following meeting transcript:\n\n"
            "* Fix spelling mistakes\n"
            "* Fix grammar\n"
            "* Improve clarity\n"
            "* Remove obvious repeated phrases\n"
            "* Do NOT change meaning\n"
            "* Do NOT remove important information\n\n"
            "Return only the cleaned transcript.\n\n"
            f"Transcript:\n{text[:12000]}\n"
        )

        try:
            chat = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2048,
            )
        except Exception as e:
            raise TranscriptCleanupError(f"Groq API request failed: {e}") from e

        choice = (chat.choices[0].message.content or "").strip()
        if not choice:
            raise TranscriptCleanupError("Groq returned an empty cleaned transcript.")
        return choice

    def answer_question(self, transcript: str, question: str) -> str:
        if not transcript.strip():
            raise QuestionAnsweringError("No transcript available for question answering.")
        if not question.strip():
            raise QuestionAnsweringError("No question provided.")
        if not self._client:
            return _local_fallback_answer(transcript, question)

        context = transcript.strip()
        if len(context) > _QA_MAX_CHARS:
            context = (
                "[Transcript truncated to the most recent meeting content]\n"
                f"{context[-_QA_MAX_CHARS:]}"
            )

        prompt = (
            "You are an AI assistant analyzing a meeting transcript.\n\n"
            "Rules:\n\n"
            "* Answer ONLY from the transcript\n"
            "* Do NOT make assumptions\n"
            "* If answer is not present, respond exactly:\n"
            "  'Not mentioned in the meeting'\n"
            "* Keep answer concise and clear\n\n"
            f"Transcript:\n{context}\n\n"
            f"Question:\n{question.strip()}\n"
        )

        try:
            chat = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=256,
            )
        except Exception as e:
            raise QuestionAnsweringError(f"Groq API request failed: {e}") from e

        choice = (chat.choices[0].message.content or "").strip()
        if not choice:
            raise QuestionAnsweringError("Groq returned an empty answer.")
        return choice


class OpenAIProviderStub(LLMProvider):
    """Placeholder for future OpenAI or other compatible APIs."""

    def generate_analysis(self, text: str) -> MeetingAnalysis:
        raise SummaryGenerationError(
            "OpenAI provider is not implemented; use Groq (set GROQ_API_KEY)."
        )

    def clean_transcript(self, text: str) -> str:
        raise TranscriptCleanupError(
            "OpenAI provider is not implemented; use Groq (set GROQ_API_KEY)."
        )

    def answer_question(self, transcript: str, question: str) -> str:
        raise QuestionAnsweringError(
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

    def generate_analysis(self, text: str) -> MeetingAnalysis:
        return self._provider.generate_analysis(text)

    def generate_summary(self, text: str) -> str:
        return self.generate_analysis(text).summary

    def fallback_analysis(self, text: str) -> MeetingAnalysis:
        return _local_fallback_analysis(text)

    def clean_transcript(self, text: str) -> str:
        return self._provider.clean_transcript(text)

    def fallback_clean_transcript(self, text: str) -> str:
        return text

    def answer_question(self, transcript: str, question: str) -> str:
        return self._provider.answer_question(transcript, question)

    def fallback_answer(self, transcript: str, question: str) -> str:
        if transcript.strip() and question.strip():
            return _local_fallback_answer(transcript, question)
        return "AI is temporarily unavailable. Please try again."


def get_ai_service() -> AIService:
    return AIService()
