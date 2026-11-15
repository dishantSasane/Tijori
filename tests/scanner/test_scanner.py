from __future__ import annotations

from datetime import date, timedelta

from tests.scanner.conftest import make_daily_candles
from trading.scanner.scanner import run_scan, scan_symbol


def test_scan_symbol_picks_up_uptrend() -> None:
    start = date(2026, 1, 1)
    closes = [100.0] * 19 + [120.0]  # closes well above its own 20d average
    candles = make_daily_candles("INFY", start, closes)
    as_of = start + timedelta(days=20)
    idea = scan_symbol("INFY", candles, as_of)
    assert idea is not None
    assert idea.rank_score > 0
    assert idea.target_price > idea.last_close
    assert idea.reconsider_price < idea.last_close


def test_scan_symbol_rejects_flat_or_down_trend() -> None:
    start = date(2026, 1, 1)
    candles = make_daily_candles("INFY", start, [100.0] * 25)
    as_of = start + timedelta(days=25)
    assert scan_symbol("INFY", candles, as_of) is None


def test_scan_symbol_only_uses_data_before_as_of() -> None:
    """A future spike must not change today's idea (no look-ahead)."""
    start = date(2026, 1, 1)
    closes = [100.0] * 20 + [500.0]  # the spike is "tomorrow" relative to as_of
    candles = make_daily_candles("INFY", start, closes)
    as_of = start + timedelta(days=20)  # the spike's own day, excluded by the window
    idea = scan_symbol("INFY", candles, as_of)
    assert idea is None  # flat history before the spike -> no uptrend signal yet


def test_run_scan_ranks_best_first() -> None:
    start = date(2026, 1, 1)
    as_of = start + timedelta(days=20)
    strong = make_daily_candles("STRONG", start, [100.0] * 19 + [150.0])
    weak = make_daily_candles("WEAK", start, [100.0] * 19 + [105.0])
    ideas = run_scan(["STRONG", "WEAK"], {"STRONG": strong, "WEAK": weak}, as_of)
    assert [idea.symbol for idea in ideas] == ["STRONG", "WEAK"]
