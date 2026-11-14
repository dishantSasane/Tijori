from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading.backtest.fills import BacktestProfile
from trading.backtest.phase1 import run_t1, run_t4
from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle


def bars(closes: list[int]) -> list[Candle]:
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
            source="fixture",
            ingest_ts=start,
        )
        for index, value in enumerate(closes)
    ]


def test_t1_runs_strategy_through_both_backtesters() -> None:
    candles = bars([10, 11, 9, 10, 13, 13, 8, 8])
    result = run_t1(
        candles,
        quantity=Decimal("1"),
        profile=BacktestProfile(),
        lookback=3,
        exit_lookback=2,
        atr_period=2,
    )
    assert len(result.signals) == 1
    assert result.result.primary == result.result.reference
    assert result.result.scorecard.trades == 1


def test_t1_window_restricts_signals_to_the_test_period() -> None:
    candles = bars([10, 11, 9, 10, 13, 13, 8, 8])
    result = run_t1(
        candles,
        quantity=Decimal("1"),
        profile=BacktestProfile(),
        lookback=3,
        exit_lookback=2,
        atr_period=2,
        signal_start=candles[5].ts_open_utc,
        signal_end=candles[7].ts_open_utc,
    )
    assert result.signals == ()
    assert result.result.scorecard.trades == 0


def test_t4_requires_full_trend_warmup_before_signalling() -> None:
    result = run_t4(
        bars([100] * 200),
        quantity=Decimal("1"),
        profile=BacktestProfile(),
    )
    assert result.signals == ()
    assert result.result.scorecard.trades == 0
