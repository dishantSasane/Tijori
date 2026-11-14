from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle
from trading.strategies.phase1 import t1_donchian, t4_exit_trigger, t4_rsi_pullback


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


def test_t1_donchian_known_answer() -> None:
    bars = candles([10, 11, 9, 10, 13])
    signals = t1_donchian(
        bars,
        [None, None, None, None, 2.0],
        lookback=3,
        atr_multiple=2,
        created_ts=bars[0].ingest_ts,
    )
    assert len(signals) == 1
    assert signals[0].entry_ref == Decimal("13")
    assert signals[0].stop == Decimal("9")
    assert signals[0].bar_ts_utc == bars[-1].ts_open_utc


def test_t1_donchian_equal_high_does_not_fire() -> None:
    bars = candles([10, 11, 9, 10, 11])
    assert (
        t1_donchian(
            bars,
            [None, None, None, None, 2.0],
            lookback=3,
            created_ts=bars[0].ingest_ts,
        )
        == []
    )


def test_t4_rsi_pullback_requires_both_conditions() -> None:
    bars = candles([105])
    signals = t4_rsi_pullback(
        bars,
        [100],
        [8],
        [2],
        created_ts=bars[0].ingest_ts,
    )
    assert len(signals) == 1
    assert t4_rsi_pullback(bars, [100], [12], [2], created_ts=bars[0].ingest_ts) == []


def test_t4_exit_trigger_rules() -> None:
    assert t4_exit_trigger(close=Decimal("106"), sma5=105, rsi=50, bars_held=1)
    assert t4_exit_trigger(close=Decimal("100"), sma5=105, rsi=71, bars_held=1)
    assert t4_exit_trigger(close=Decimal("100"), sma5=105, rsi=50, bars_held=5)
    assert not t4_exit_trigger(close=Decimal("100"), sma5=105, rsi=50, bars_held=4)
