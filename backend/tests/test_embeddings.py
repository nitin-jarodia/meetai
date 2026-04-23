"""Tests for the pluggable embedding providers."""

from __future__ import annotations

import pytest

from app.services.embedding_service import (
    HashEmbeddingProvider,
    cosine_similarity,
    get_embedding_provider,
    reset_embedding_provider,
)


@pytest.fixture(autouse=True)
def reset_singleton():
    reset_embedding_provider()
    yield
    reset_embedding_provider()


def test_hash_provider_is_deterministic() -> None:
    provider = HashEmbeddingProvider(dimensions=128)
    v1 = provider.embed("the quarterly sync was productive")
    v2 = provider.embed("the quarterly sync was productive")
    assert v1 == v2
    assert len(v1) == 128


def test_hash_provider_vectors_are_unit_norm() -> None:
    provider = HashEmbeddingProvider(dimensions=64)
    vec = provider.embed("meeting notes action items")
    norm = sum(x * x for x in vec) ** 0.5
    assert abs(norm - 1.0) < 1e-6


def test_cosine_similarity_ranks_related_higher() -> None:
    provider = HashEmbeddingProvider(dimensions=256)
    query = provider.embed("budget approval for marketing")
    related = provider.embed("we approved the marketing budget")
    unrelated = provider.embed("the coffee machine broke again")
    assert cosine_similarity(query, related) > cosine_similarity(query, unrelated)


def test_cosine_similarity_handles_zero_vectors() -> None:
    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([0.0, 0.0], [0.0, 0.0]) == 0.0
    assert cosine_similarity([1.0, 0.0], []) == 0.0


def test_get_embedding_provider_returns_singleton() -> None:
    a = get_embedding_provider()
    b = get_embedding_provider()
    assert a is b
    assert a.version.startswith("hash-v1:") or a.version.startswith("st:")


def test_embed_many_matches_single_embed() -> None:
    provider = HashEmbeddingProvider(dimensions=128)
    texts = ["hello there", "general kenobi", "meeting summary"]
    batch = provider.embed_many(texts)
    assert len(batch) == 3
    for text, vec in zip(texts, batch):
        assert vec == provider.embed(text)
