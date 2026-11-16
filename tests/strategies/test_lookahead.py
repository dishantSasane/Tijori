"""Prefix tests check that future candles cannot revise past entry signals."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle, Signal
from trading.indicators.moving_averages import sma
from trading.indicators.technical import atr, rsi
from trading.strategies.p1_candidates import generate_p1_daily_signals
from trading.strategies.phase1 import t1_donchian, t4_rsi_pullback


def candles(closes: list[int]) -> list[Candle]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Candle(
            market=MarketId.IN_EQUITY,
            symbol="TEST",
            timeframe=Timeframe.D1,
            ts_open_utc=start + timedelta(days=index),
            open=Decimal(value),
            high=Decimal(value + 1),
            low=Decimal(value - 1),
            close=Decimal(value),
            volume=Decimal("1000"),
            source="test",
            ingest_ts=start,
        )
        for index, value in enumerate(closes)
    ]


def signals_for_prefix(bars: list[Candle], strategy: str) -> list[Signal]:
    closes = [float(bar.close) for bar in bars]
    highs = [float(bar.high) for bar in bars]
    lows = [float(bar.low) for bar in bars]
    atr_values = atr(highs, lows, closes, 2)
    if strategy == "t1":
        return t1_donchian(bars, atr_values, lookback=3, created_ts=bars[0].ingest_ts)
    return t4_rsi_pullback(
        bars, sma(closes, 20), rsi(closes, 2), atr_values, created_ts=bars[0].ingest_ts
    )


def test_future_bars_do_not_change_t1_or_t4_past_signals() -> None:
    # A breakout followed by a pullback yields at least one signal for each
    # strategy. Recalculate all indicators using each prefix, as live would.
    bars = candles([100] * 20 + [110, 109, 108, 107, 106, 105, 104, 103, 102])
    for strategy in ("t1", "t4"):
        full_signals = signals_for_prefix(bars, strategy)
        assert full_signals, f"{strategy} fixture must produce signals"
        for end in range(1, len(bars) + 1):
            prefix_signals = signals_for_prefix(bars[:end], strategy)
            expected = [s for s in full_signals if s.bar_ts_utc <= bars[end - 1].ts_open_utc]
            assert [s.model_dump(exclude={"id"}) for s in prefix_signals] == [
                s.model_dump(exclude={"id"}) for s in expected
            ], (strategy, end)


def test_future_bars_do_not_change_t2_or_t6_past_signals() -> None:
    start = datetime(2020, 1, 1, tzinfo=UTC)
    fixtures = {
        "t2-ema20-50-adx25-v1": [200 - index for index in range(60)]
        + [140 + 3 * index for index in range(80)],
        "t6-bollinger20-2-v1": [100] * 205 + [99],
    }
    for candidate_id, closes in fixtures.items():
        bars = candles(closes)
        full_signals = generate_p1_daily_signals(candidate_id, bars, created_ts=start)
        assert full_signals, f"{candidate_id} fixture must produce signals"
        for end in range(1, len(bars) + 1):
            prefix_signals = generate_p1_daily_signals(
                candidate_id,
                bars[:end],
                created_ts=start,
            )
            expected = [
                signal for signal in full_signals if signal.bar_ts_utc <= bars[end - 1].ts_open_utc
            ]
            assert [signal.model_dump(exclude={"id"}) for signal in prefix_signals] == [
                signal.model_dump(exclude={"id"}) for signal in expected
            ], (candidate_id, end)
