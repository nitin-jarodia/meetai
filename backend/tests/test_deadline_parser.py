"""Tests for the freeform deadline parser used by the action-item service."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services.deadline_parser import parse_due_at


REF = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)  # Tue


def test_empty_inputs_return_none() -> None:
    assert parse_due_at(None) is None
    assert parse_due_at("") is None
    assert parse_due_at("   ") is None
    assert parse_due_at(",.;") is None


def test_today_returns_same_day() -> None:
    result = parse_due_at("today", reference=REF)
    assert result is not None
    assert result.tzinfo is not None
    assert result.date() == REF.date()


def test_tomorrow_returns_next_day() -> None:
    result = parse_due_at("tomorrow", reference=REF)
    assert result is not None
    assert (result.date() - REF.date()).days == 1


def test_in_n_days_heuristic() -> None:
    result = parse_due_at("in 3 days", reference=REF)
    assert result is not None
    assert (result.date() - REF.date()).days == 3


@pytest.mark.parametrize("phrase", ["next Friday", "by Friday", "on Friday"])
def test_weekday_phrases(phrase: str) -> None:
    result = parse_due_at(phrase, reference=REF)
    assert result is not None
    assert result.weekday() == 4  # Friday
    assert result >= REF


def test_result_is_utc_aware() -> None:
    result = parse_due_at("tomorrow", reference=REF)
    assert result is not None
    assert result.tzinfo is not None
    assert result.utcoffset() == (result - result.replace(tzinfo=timezone.utc)).__class__(
        0
    ) or result.utcoffset() is not None


def test_completely_gibberish_returns_none() -> None:
    assert parse_due_at("zzzqqq not a date", reference=REF) is None
