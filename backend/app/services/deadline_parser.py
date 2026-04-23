"""Parse freeform deadline strings into UTC-aware datetimes.

Uses `dateparser` when installed; falls back to a small set of heuristics.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def parse_due_at(
    text: str | None,
    *,
    reference: datetime | None = None,
    prefer: Iterable[str] = ("day", "month", "year"),
) -> datetime | None:
    """
    Return a timezone-aware UTC datetime, or None if the string is empty /
    unparseable. ``reference`` lets callers pin "now" for deterministic tests.
    """
    if not text:
        return None
    cleaned = text.strip().strip(".,;:")
    if not cleaned:
        return None

    now = reference or datetime.now(timezone.utc)

    try:
        import dateparser  # type: ignore
    except ImportError:
        return _heuristic_parse(cleaned, now)

    try:
        parsed = dateparser.parse(
            cleaned,
            settings={
                "RELATIVE_BASE": now.replace(tzinfo=None),
                "PREFER_DATES_FROM": "future",
                "TIMEZONE": "UTC",
                "RETURN_AS_TIMEZONE_AWARE": True,
            },
        )
    except Exception:
        parsed = None

    if parsed is None:
        return _heuristic_parse(cleaned, now)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)
    return parsed


def _heuristic_parse(text: str, now: datetime) -> datetime | None:
    """Tiny fallback covering a few common phrases without the dateparser dep."""
    lowered = text.lower().strip()
    if lowered in ("today",):
        return now.replace(hour=17, minute=0, second=0, microsecond=0)
    if lowered in ("tomorrow",):
        return (now + timedelta(days=1)).replace(
            hour=17, minute=0, second=0, microsecond=0
        )
    if lowered.startswith("in "):
        rest = lowered[3:].strip()
        try:
            num, unit = rest.split()
            days = int(num)
            if unit.startswith("day"):
                return now + timedelta(days=days)
            if unit.startswith("week"):
                return now + timedelta(weeks=days)
            if unit.startswith("hour"):
                return now + timedelta(hours=days)
        except ValueError:
            return None
    for prefix in ("by ", "before ", "on ", "next "):
        if lowered.startswith(prefix):
            rest = lowered[len(prefix) :].strip()
            if rest in _WEEKDAYS:
                target = _WEEKDAYS[rest]
                today = now.weekday()
                delta = (target - today) % 7
                delta = delta or 7
                return (now + timedelta(days=delta)).replace(
                    hour=17, minute=0, second=0, microsecond=0
                )
    return None
