from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading.core.enums import MarketId, OrderSide, Timeframe
from trading.core.models import Candle, Signal
from trading.strategies.daily_candidates import make_daily_exit_condition


def make_candles(count: int) -> list[Candle]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Candle(
            market=MarketId.IN_EQUITY,
            symbol="TEST",
            timeframe=Timeframe.D1,
            ts_open_utc=start + timedelta(days=index),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            volume=Decimal("1000"),
            source="test",
            ingest_ts=start,
        )
        for index in range(count)
    ]


def make_signal(candles: list[Candle]) -> Signal:
    return Signal(
        market=MarketId.IN_EQUITY,
        symbol="TEST",
        timeframe=Timeframe.D1,
        strategy_id="test",
        strategy_version="1.0.0",
        side=OrderSide.BUY,
        entry_ref=Decimal("100"),
        stop=Decimal("90"),
        bar_ts_utc=candles[0].ts_open_utc,
        created_ts=candles[0].ingest_ts,
    )


def test_t1_exit_callback_uses_prior_m_lows_and_excludes_current_bar() -> None:
    bars = make_candles(12)
    bars[11] = bars[11].model_copy(update={"low": Decimal("80"), "close": Decimal("89")})
    callback = make_daily_exit_condition("t1-donchian-n20-m10-k2-v1", bars)
    assert callback(make_signal(bars), 11, bars[11])


def test_t2_exit_callback_uses_bearish_ema_relation() -> None:
    bars = make_candles(3)
    callback = make_daily_exit_condition(
        "t2-ema20-50-adx25-v1",
        bars,
        fast_ema=[10, 9, 8],
        slow_ema=[10, 10, 10],
    )
    assert callback(make_signal(bars), 2, bars[2])


def test_t4_exit_callback_applies_five_post_entry_bar_time_stop() -> None:
    bars = make_candles(7)
    callback = make_daily_exit_condition(
        "t4-rsi2-10-atr25-v1",
        bars,
        sma5=[None] * len(bars),
        rsi_values=[None] * len(bars),
    )
    signal = make_signal(bars)
    assert not callback(signal, 4, bars[4])  # four bars including entry have closed
    assert callback(signal, 5, bars[5])  # fifth bar closes here


def test_t6_exit_callback_applies_ten_post_entry_bar_time_stop() -> None:
    bars = make_candles(12)
    callback = make_daily_exit_condition(
        "t6-bollinger20-2-v1",
        bars,
        middle_band=[None] * len(bars),
    )
    signal = make_signal(bars)
    assert not callback(signal, 9, bars[9])
    assert callback(signal, 10, bars[10])


def test_daily_exit_callback_requires_the_candidate_indicators() -> None:
    bars = make_candles(3)
    with pytest.raises(ValueError, match="fast_ema and slow_ema"):
        make_daily_exit_condition("t2-ema20-50-adx25-v1", bars)
