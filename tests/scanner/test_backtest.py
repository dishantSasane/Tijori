from __future__ import annotations

from datetime import date, timedelta

from tests.scanner.conftest import make_daily_candles
from trading.scanner.backtest import replay, summarize


def test_replay_scores_forward_return_without_lookahead() -> None:
    start = date(2026, 1, 1)
    # Uptrend breakout on day 20, then keeps rising for the 10-day horizon.
    closes = [100.0] * 19 + [150.0] + [160.0] * 11
    candles = make_daily_candles("UP", start, closes)
    session_dates = [start + timedelta(days=20)]

    outcomes = replay(["UP"], {"UP": candles}, session_dates, horizon_days=10)
    assert len(outcomes) == 1
    assert outcomes[0].idea.symbol == "UP"
    assert outcomes[0].forward_return_pct is not None
    assert outcomes[0].forward_return_pct > 0

    stats = summarize(outcomes)
    assert stats["count"] == 1
    assert stats["hit_rate"] == 1


def test_replay_marks_unresolved_outcomes_as_none() -> None:
    start = date(2026, 1, 1)
    closes = [100.0] * 19 + [150.0]  # no future candles to measure the horizon against
    candles = make_daily_candles("UP", start, closes)
    session_dates = [start + timedelta(days=20)]

    outcomes = replay(["UP"], {"UP": candles}, session_dates, horizon_days=10)
    assert outcomes[0].forward_return_pct is None
    assert summarize(outcomes) == {"count": 0, "hit_rate": 0, "avg_return_pct": 0}
