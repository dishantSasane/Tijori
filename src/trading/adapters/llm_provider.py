"""LLMProvider Protocol + fake. The Brain is advisory and never in the hot path
(AGENTS.md §4.6); invalid/missing output is treated as absent, never as support.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from trading.core.enums import BrainLabel
from trading.core.models import BrainVerdict, Signal


class LLMProvider(Protocol):
    def get_verdict(self, signal: Signal, context: str) -> BrainVerdict | None:
        """Return a schema-valid verdict, or None if the call failed, timed out,
        the output didn't validate, or the budget guard blocked the call. A
        caller must treat None exactly like BrainLabel.NEUTRAL with multiplier 1.
        """
        ...


class FakeLLMProvider:
    """Returns a fixed verdict (or None) regardless of input. Used in tests to
    exercise both the "Brain present" and "Brain absent/invalid" risk-engine paths.
    """

    def __init__(self, verdict: BrainVerdict | None = None) -> None:
        self._verdict = verdict

    def get_verdict(self, signal: Signal, context: str) -> BrainVerdict | None:
        if self._verdict is None:
            return None
        return self._verdict.model_copy(update={"signal_id": signal.id})


def default_absent_verdict(signal_id: str, *, now: datetime) -> BrainVerdict:
    """What the risk engine should treat a missing/invalid Brain call as.

    `now` comes from the caller's injected Clock (AGENTS.md §6) — this
    function never reads wall-clock time itself.
    """
    from decimal import Decimal

    return BrainVerdict(
        signal_id=signal_id, label=BrainLabel.NEUTRAL, size_multiplier=Decimal(1), created_ts=now
    )
