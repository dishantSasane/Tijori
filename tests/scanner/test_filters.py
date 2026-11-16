from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from tests.scanner.conftest import make_daily_candles
from trading.scanner.filters import average_turnover, passes_data_quality, passes_liquidity


def test_passes_data_quality_rejects_stale_history() -> None:
    start = date(2026, 1, 1)
    candles = make_daily_candles("INFY", start, [100.0] * 25)
    as_of = start + timedelta(days=40)  # far past the last candle
    assert passes_data_quality(candles, as_of) is False


def test_passes_data_quality_accepts_fresh_history() -> None:
    start = date(2026, 1, 1)
    candles = make_daily_candles("INFY", start, [100.0] * 25)
    as_of = start + timedelta(days=25)
    assert passes_data_quality(candles, as_of) is True


def test_liquidity_filter_respects_threshold() -> None:
    start = date(2026, 1, 1)
    # close=100, volume=1_000_000 -> turnover 100_000_000, well above the floor.
    candles = make_daily_candles("INFY", start, [100.0] * 25)
    as_of = start + timedelta(days=25)
    assert passes_liquidity(candles, as_of) is True
    assert average_turnover(candles, as_of) == Decimal("100000000")


def test_liquidity_filter_rejects_thin_turnover() -> None:
    start = date(2026, 1, 1)
    candles = make_daily_candles("PENNY", start, [1.0] * 25, volume=Decimal("100"))
    as_of = start + timedelta(days=25)
    assert passes_liquidity(candles, as_of) is False


def test_filters_never_see_the_as_of_day_itself() -> None:
    """The window strictly excludes ``as_of`` -- the no-look-ahead guarantee."""
    start = date(2026, 1, 1)
    candles = make_daily_candles("INFY", start, [100.0] * 20 + [100000.0])
    as_of = start + timedelta(days=20)  # the spike candle's own day
    # If the spike leaked into the window, turnover would be enormous.
    assert average_turnover(candles, as_of) < Decimal("1000000000")
