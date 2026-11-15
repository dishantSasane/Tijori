from __future__ import annotations

from decimal import Decimal

from tests.execution.conftest import NOW
from trading.core.enums import OutcomeResult
from trading.execution.outcome_tracker import OutcomeTracker


def test_record_and_get_roundtrip(store):
    tracker = OutcomeTracker(store)
    tracker.record(
        "sig-1",
        OutcomeResult.TARGET_HIT,
        pct_after_costs=Decimal("1.23"),
        bars_held=3,
        closed_ts=NOW,
    )
    outcome = tracker.get("sig-1")
    assert outcome is not None
    assert outcome.result == OutcomeResult.TARGET_HIT
    assert outcome.pct_after_costs == Decimal("1.23")
    assert outcome.bars_held == 3


def test_get_missing_returns_none(store):
    tracker = OutcomeTracker(store)
    assert tracker.get("nope") is None
