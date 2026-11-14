"""Injected clock. Core logic must never call datetime.now()/utcnow() directly
(AGENTS.md §6) so that backtests and tests are deterministic.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Current time, timezone-aware, UTC."""
        ...


class SystemClock:
    """Real wall-clock time. Used only at process entry points."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    """Returns a fixed instant. Used in tests."""

    def __init__(self, at: datetime) -> None:
        if at.tzinfo is None:
            raise ValueError("FixedClock requires a timezone-aware datetime")
        self._at = at.astimezone(UTC)

    def now(self) -> datetime:
        return self._at

    def advance(self, *, seconds: float) -> None:
        from datetime import timedelta

        self._at = self._at + timedelta(seconds=seconds)
