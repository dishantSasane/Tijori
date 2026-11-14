"""Phase-1 strategy backtest entry points for T1 and T4."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from trading.backtest.fills import BacktestProfile
from trading.backtest.validation import ValidatedBacktest, validate_long_only
from trading.core.models import Candle, Signal
from trading.indicators.moving_averages import sma
from trading.indicators.technical import atr, donchian, rsi
from trading.strategies.phase1 import t1_donchian, t4_exit_trigger, t4_rsi_pullback


@dataclass(frozen=True)
class StrategyBacktest:
    """Signals plus an equivalence-checked backtest and scorecard."""

    strategy_id: str
    signals: tuple[Signal, ...]
    result: ValidatedBacktest


def run_t1(
    candles: list[Candle],
    *,
    quantity: Decimal,
    profile: BacktestProfile,
    lookback: int = 20,
    exit_lookback: int = 10,
    atr_period: int = 14,
    atr_multiple: Decimal = Decimal("2"),
    signal_start: datetime | None = None,
    signal_end: datetime | None = None,
) -> StrategyBacktest:
    """Run T1 Donchian breakout with its closed-bar lower-channel exit."""
    _validate_candles(candles)
    highs, lows, closes = _ohlc_as_float(candles)
    atr_values = atr(highs, lows, closes, atr_period)
    signals = t1_donchian(
        candles,
        atr_values,
        lookback=lookback,
        exit_lookback=exit_lookback,
        atr_multiple=atr_multiple,
        created_ts=candles[0].ingest_ts,
    )
    signals = _restrict_signals(signals, signal_start=signal_start, signal_end=signal_end)
    _, lower = donchian(highs, lows, exit_lookback)

    def exit_rule(signal: Signal, index: int, candle: Candle) -> bool:
        del signal
        channel = lower[index]
        return channel is not None and float(candle.close) < channel

    return _validated("t1_donchian", candles, signals, quantity, profile, exit_rule)


def run_t4(
    candles: list[Candle],
    *,
    quantity: Decimal,
    profile: BacktestProfile,
    trend_period: int = 200,
    rsi_period: int = 2,
    atr_period: int = 14,
    rsi_threshold: Decimal = Decimal("10"),
    atr_multiple: Decimal = Decimal("2.5"),
    signal_start: datetime | None = None,
    signal_end: datetime | None = None,
) -> StrategyBacktest:
    """Run T4 RSI(2) pullback with its closed-bar/time exits."""
    _validate_candles(candles)
    highs, lows, closes = _ohlc_as_float(candles)
    atr_values = atr(highs, lows, closes, atr_period)
    sma_values = sma(closes, trend_period)
    rsi_values = rsi(closes, rsi_period)
    sma5_values = sma(closes, 5)
    signals = t4_rsi_pullback(
        candles,
        sma_values,
        rsi_values,
        atr_values,
        rsi_threshold=rsi_threshold,
        atr_multiple=atr_multiple,
        created_ts=candles[0].ingest_ts,
    )
    signals = _restrict_signals(signals, signal_start=signal_start, signal_end=signal_end)

    def exit_rule(signal: Signal, index: int, candle: Candle) -> bool:
        entry_index = next(
            item
            for item, candidate in enumerate(candles)
            if candidate.ts_open_utc == signal.bar_ts_utc
        )
        return t4_exit_trigger(
            close=candle.close,
            sma5=sma5_values[index],
            rsi=rsi_values[index],
            bars_held=index - entry_index,
        )

    return _validated("t4_rsi_pullback", candles, signals, quantity, profile, exit_rule)


def _validated(
    strategy_id: str,
    candles: list[Candle],
    signals: list[Signal],
    quantity: Decimal,
    profile: BacktestProfile,
    exit_rule: Callable[[Signal, int, Candle], bool],
) -> StrategyBacktest:
    return StrategyBacktest(
        strategy_id=strategy_id,
        signals=tuple(signals),
        result=validate_long_only(
            candles,
            signals,
            quantity=quantity,
            profile=profile,
            condition_exit=exit_rule,
        ),
    )


def _validate_candles(candles: list[Candle]) -> None:
    if not candles:
        raise ValueError("at least one candle is required")
    instrument = (candles[0].market, candles[0].symbol, candles[0].timeframe)
    if any((candle.market, candle.symbol, candle.timeframe) != instrument for candle in candles):
        raise ValueError("strategy backtest requires one instrument")
    if any(
        left.ts_open_utc >= right.ts_open_utc
        for left, right in zip(candles, candles[1:], strict=False)
    ):
        raise ValueError("candles must be strictly ordered by open time")


def _restrict_signals(
    signals: list[Signal],
    *,
    signal_start: datetime | None,
    signal_end: datetime | None,
) -> list[Signal]:
    if signal_start is not None and signal_end is not None and signal_start >= signal_end:
        raise ValueError("signal_start must precede signal_end")
    return [
        signal
        for signal in signals
        if (signal_start is None or signal.bar_ts_utc >= signal_start)
        and (signal_end is None or signal.bar_ts_utc < signal_end)
    ]


def _ohlc_as_float(candles: list[Candle]) -> tuple[list[float], list[float], list[float]]:
    return (
        [float(candle.high) for candle in candles],
        [float(candle.low) for candle in candles],
        [float(candle.close) for candle in candles],
    )
