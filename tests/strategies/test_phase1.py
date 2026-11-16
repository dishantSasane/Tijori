from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle
from trading.strategies.daily_candidates import (
    t2_ema_adx,
    t2_exit_trigger,
    t6_bollinger_reversion,
    t6_exit_trigger,
)
from trading.strategies.phase1 import (
    t1_donchian,
    t1_exit_trigger,
    t4_exit_trigger,
    t4_rsi_pullback,
)


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
    bars[1] = bars[1].model_copy(update={"high": Decimal("11")})
    bars[2] = bars[2].model_copy(update={"high": Decimal("9")})
    bars[3] = bars[3].model_copy(update={"high": Decimal("10")})
    assert (
        t1_donchian(
            bars,
            [None, None, None, None, 2.0],
            lookback=3,
            created_ts=bars[0].ingest_ts,
        )
        == []
    )


def test_t1_exit_uses_strict_prior_low_channel() -> None:
    lows = [Decimal("10"), Decimal("8")]
    assert not t1_exit_trigger(close=Decimal("8"), prior_lows=lows, exit_lookback=2)
    assert t1_exit_trigger(close=Decimal("7.99"), prior_lows=lows, exit_lookback=2)
    with pytest.raises(ValueError, match="complete exit lookback"):
        t1_exit_trigger(close=Decimal("7"), prior_lows=lows[:1], exit_lookback=2)


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


def test_t2_requires_bullish_cross_and_adx_strictly_above_threshold() -> None:
    bars = candles([10, 11])
    signals = t2_ema_adx(
        bars,
        [9, 11],
        [10, 10],
        [25, 25.01],
        [1, 1],
        created_ts=bars[0].ingest_ts,
    )
    assert len(signals) == 1
    assert signals[0].entry_ref == Decimal("11")
    assert signals[0].stop == Decimal("9")
    assert not t2_exit_trigger(fast_ema=10, slow_ema=10)
    assert t2_exit_trigger(fast_ema=9.99, slow_ema=10)


def test_t2_does_not_reenter_when_fast_ema_was_already_above() -> None:
    bars = candles([10, 11])
    assert (
        t2_ema_adx(
            bars,
            [11, 12],
            [10, 10],
            [30, 30],
            [1, 1],
            created_ts=bars[0].ingest_ts,
        )
        == []
    )


def test_t6_strict_lower_band_and_adx_gate_and_exits() -> None:
    bars = candles([9, 8])
    signals = t6_bollinger_reversion(
        bars,
        [9, 9],
        [10, 10],
        [19, 19],
        [1, 1],
        created_ts=bars[0].ingest_ts,
    )
    assert [signal.entry_ref for signal in signals] == [Decimal("8")]
    assert not t6_exit_trigger(close=Decimal("9"), middle_band=10, bars_held=9)
    assert t6_exit_trigger(close=Decimal("10"), middle_band=10, bars_held=1)
    assert t6_exit_trigger(close=Decimal("8"), middle_band=10, bars_held=10)


def test_daily_candidates_reject_nonfinite_indicator_values() -> None:
    bars = candles([10, 11])
    with pytest.raises(ValueError, match="finite"):
        t2_ema_adx(
            bars,
            [9, float("nan")],
            [10, 10],
            [30, 30],
            [1, 1],
            created_ts=bars[0].ingest_ts,
        )
