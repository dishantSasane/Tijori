"""Covers docs/specs/TEST_SPEC_CANDLES.md §1 and the extra rules pinned down
in docs/specs/CANDLE_BUILDER_AND_SCHEDULER_SPEC.md §2.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading.candles.builder import (
    CandleAggregator,
    CandleBuilder,
    candle_from_daily_bar,
    floor_to_timeframe,
)
from trading.core.enums import MarketId, Timeframe
from trading.core.models import Tick


def _tick(ts: datetime, price: str, size: str = "10") -> Tick:
    return Tick(
        market=MarketId.IN_EQUITY,
        symbol="HDFCBANK",
        ts_utc=ts,
        price=Decimal(price),
        size=Decimal(size),
    )


def test_bar_boundary_alignment_known_answer() -> None:
    # 09:15:00 IST == 03:45:00 UTC (non-DST). A tick at 03:47:32 UTC belongs
    # to the bar opening 03:45:00 UTC.
    ts = datetime(2026, 1, 5, 3, 47, 32, tzinfo=UTC)
    window = floor_to_timeframe(ts, Timeframe.M5)
    assert window == datetime(2026, 1, 5, 3, 45, 0, tzinfo=UTC)


def test_bar_closes_on_timer_not_on_next_tick() -> None:
    builder = CandleBuilder(market=MarketId.IN_EQUITY, symbol="HDFCBANK", timeframe=Timeframe.M5)
    t0 = datetime(2026, 1, 5, 3, 45, 0, tzinfo=UTC)
    builder.push_tick(_tick(t0 + timedelta(seconds=10), "100"))
    # advance() to exactly the close boundary -- no next tick has arrived.
    closed = builder.advance(t0 + timedelta(minutes=5))
    assert len(closed) == 1
    assert closed[0].close == Decimal("100")
    assert builder.poll_closed_candles() == closed


def test_zero_tick_window_still_closes_carrying_forward_close() -> None:
    builder = CandleBuilder(market=MarketId.IN_EQUITY, symbol="HDFCBANK", timeframe=Timeframe.M5)
    t0 = datetime(2026, 1, 5, 3, 45, 0, tzinfo=UTC)
    builder.push_tick(_tick(t0 + timedelta(seconds=10), "100"))
    builder.advance(t0 + timedelta(minutes=5))  # closes bar 1 at 100
    # No ticks at all in the next window -- still closes as a zero-volume bar.
    closed = builder.advance(t0 + timedelta(minutes=10))
    assert len(closed) == 1
    bar2 = closed[0]
    assert bar2.volume == Decimal(0)
    assert bar2.open == bar2.high == bar2.low == bar2.close == Decimal("100")


def test_first_bar_ever_with_zero_ticks_is_skipped_not_invented() -> None:
    builder = CandleBuilder(market=MarketId.IN_EQUITY, symbol="HDFCBANK", timeframe=Timeframe.M5)
    t0 = datetime(2026, 1, 5, 3, 45, 0, tzinfo=UTC)
    closed = builder.advance(t0 + timedelta(minutes=5))
    assert closed == []
    assert builder.no_prior_close_skipped == [t0]


def test_out_of_order_tick_open_is_chronologically_earliest_by_own_timestamp() -> None:
    builder = CandleBuilder(market=MarketId.IN_EQUITY, symbol="HDFCBANK", timeframe=Timeframe.M5)
    t0 = datetime(2026, 1, 5, 3, 45, 0, tzinfo=UTC)
    # Processed out of order: the tick timestamped earlier arrives second.
    builder.push_tick(_tick(t0 + timedelta(seconds=20), "105"))
    builder.push_tick(_tick(t0 + timedelta(seconds=5), "100"))
    closed = builder.advance(t0 + timedelta(minutes=5))
    assert closed[0].open == Decimal("100")  # earliest by its own ts, not by processing order
    assert closed[0].close == Decimal("105")  # latest by its own ts


def test_late_tick_for_already_closed_bar_is_dropped_not_reopened() -> None:
    builder = CandleBuilder(market=MarketId.IN_EQUITY, symbol="HDFCBANK", timeframe=Timeframe.M5)
    t0 = datetime(2026, 1, 5, 3, 45, 0, tzinfo=UTC)
    builder.push_tick(_tick(t0 + timedelta(seconds=10), "100"))
    closed = builder.advance(t0 + timedelta(minutes=5))
    emitted = closed[0]
    # A delayed retry for the already-closed window.
    builder.push_tick(_tick(t0 + timedelta(seconds=30), "999"))
    assert builder.poll_closed_candles() == [emitted]  # unchanged, frozen
    assert len(builder.dropped_late_ticks) == 1


def test_poll_closed_candles_never_returns_a_still_open_bar() -> None:
    builder = CandleBuilder(market=MarketId.IN_EQUITY, symbol="HDFCBANK", timeframe=Timeframe.M5)
    t0 = datetime(2026, 1, 5, 3, 45, 0, tzinfo=UTC)
    builder.push_tick(_tick(t0 + timedelta(seconds=10), "100"))
    as_of = t0 + timedelta(minutes=2)  # well before this bar's close boundary
    assert builder.poll_closed_candles() == []
    for candle in builder.poll_closed_candles():
        assert candle.ts_open_utc + timedelta(minutes=5) <= as_of


def test_daily_bar_from_provider_file_validates_identically_distinct_source() -> None:
    ts = datetime(2026, 1, 5, 0, 0, tzinfo=UTC)
    daily = candle_from_daily_bar(
        market=MarketId.IN_EQUITY,
        symbol="HDFCBANK",
        ts_open_utc=ts,
        open_=Decimal(100),
        high=Decimal(105),
        low=Decimal(99),
        close=Decimal(102),
        volume=Decimal(1_000_000),
        ingest_ts=ts,
    )
    assert daily.source == "nse_bhavcopy"

    builder = CandleBuilder(market=MarketId.IN_EQUITY, symbol="HDFCBANK", timeframe=Timeframe.D1)
    builder.push_tick(_tick(ts + timedelta(hours=1), "100"))
    tick_built = builder.advance(ts + timedelta(days=1))[0]
    assert tick_built.source == "tick_builder"
    assert daily.market == tick_built.market and daily.symbol == tick_built.symbol


def test_candle_aggregator_rolls_up_closed_bars_into_bigger_timeframe() -> None:
    base = CandleBuilder(market=MarketId.IN_EQUITY, symbol="HDFCBANK", timeframe=Timeframe.M1)
    agg = CandleAggregator(market=MarketId.IN_EQUITY, symbol="HDFCBANK", timeframe=Timeframe.M5)
    t0 = datetime(2026, 1, 5, 3, 45, 0, tzinfo=UTC)
    prices = ["100", "101", "99", "103", "102"]
    for i, price in enumerate(prices):
        base.push_tick(_tick(t0 + timedelta(minutes=i, seconds=1), price))
    base.advance(t0 + timedelta(minutes=5))
    for sub in base.poll_closed_candles():
        agg.push_candle(sub)
    closed = agg.advance(t0 + timedelta(minutes=5))
    assert len(closed) == 1
    rolled = closed[0]
    assert rolled.open == Decimal("100")
    assert rolled.close == Decimal("102")
    assert rolled.high == Decimal("103")
    assert rolled.low == Decimal("99")
