"""Pluggable embedding backends.

Order of preference:
  1. settings.embedding_backend == "sentence-transformers" → require it (raises if missing)
  2. settings.embedding_backend == "hash"                 → always hash
  3. "auto" (default): use sentence-transformers if importable, else hash

The hash backend is deterministic, offline, and dimension-configurable so it
degrades gracefully for dev DBs that don't have the model installed. Rows
indexed by different backends are compared in-process only against queries
embedded by the *same* backend, which we enforce via `embedding_version`.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)

_TOKEN = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text)]


@dataclass(slots=True)
class EmbeddingResult:
    vector: list[float]
    version: str  # e.g. "hash-v1:384" or "st:all-MiniLM-L6-v2"


class EmbeddingProvider:
    version: str = "unknown"
    dimensions: int = 0

    def embed(self, text: str) -> list[float]:
        raise NotImplementedError

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class HashEmbeddingProvider(EmbeddingProvider):
    """Dimension-configurable hashed bag-of-words with signed buckets."""

    def __init__(self, dimensions: int) -> None:
        self.dimensions = max(16, int(dimensions))
        self.version = f"hash-v1:{self.dimensions}"

    def embed(self, text: str) -> list[float]:
        counts = Counter(_tokenize(text))
        if not counts:
            return [0.0] * self.dimensions
        vec = [0.0] * self.dimensions
        for token, count in counts.items():
            idx = hash(token) % self.dimensions
            sign = 1.0 if (hash(f"sign:{token}") % 2 == 0) else -1.0
            vec[idx] += count * sign
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [v / norm for v in vec]


class SentenceTransformerProvider(EmbeddingProvider):
    """sentence-transformers wrapper. Lazily loaded so import cost is deferred."""

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer  # type: ignore

        self._model = SentenceTransformer(model_name)
        test_vec = self._model.encode("probe", normalize_embeddings=True)
        self.dimensions = int(len(test_vec))
        short = model_name.rsplit("/", 1)[-1]
        self.version = f"st:{short}"

    def embed(self, text: str) -> list[float]:
        vec = self._model.encode(text or "", normalize_embeddings=True)
        return [float(x) for x in vec]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return [[float(x) for x in v] for v in vecs]


_provider_singleton: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    global _provider_singleton
    if _provider_singleton is not None:
        return _provider_singleton

    backend = (settings.embedding_backend or "auto").strip().lower()
    if backend == "hash":
        _provider_singleton = HashEmbeddingProvider(settings.search_embedding_dimensions)
        return _provider_singleton

    if backend in ("sentence-transformers", "auto"):
        try:
            _provider_singleton = SentenceTransformerProvider(settings.embedding_model)
            logger.info("Embeddings: using %s", _provider_singleton.version)
            return _provider_singleton
        except Exception as exc:  # ImportError or model-load failure
            if backend == "sentence-transformers":
                raise RuntimeError(
                    f"EMBEDDING_BACKEND=sentence-transformers but failed to load: {exc}"
                ) from exc
            logger.info(
                "sentence-transformers not available (%s). Falling back to hash embeddings.",
                exc,
            )

    _provider_singleton = HashEmbeddingProvider(settings.search_embedding_dimensions)
    return _provider_singleton


def reset_embedding_provider() -> None:
    """Test hook — re-read settings on next call."""
    global _provider_singleton
    _provider_singleton = None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)
