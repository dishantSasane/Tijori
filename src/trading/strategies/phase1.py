"""Phase-1 long-only signal rules from ``docs/specs/STRATEGY_SPEC.md``."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from trading.core.enums import OrderSide
from trading.core.models import Candle, Signal


def _decimal(value: float | int | Decimal) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def t1_donchian(
    candles: Sequence[Candle],
    atr_values: Sequence[float | None],
    *,
    lookback: int = 20,
    exit_lookback: int = 10,
    atr_multiple: float = 2.0,
    strategy_version: str = "1.0.0",
    created_ts: datetime,
) -> list[Signal]:
    """Emit T1 entries when close exceeds the previous ``lookback`` highs."""
    if lookback <= 0 or exit_lookback <= 0 or atr_multiple <= 0:
        raise ValueError("lookbacks and atr_multiple must be positive")
    if len(candles) != len(atr_values):
        raise ValueError("candles and atr_values must have equal lengths")
    signals: list[Signal] = []
    for index, candle in enumerate(candles):
        if index < lookback:
            continue
        atr_value = atr_values[index]
        if atr_value is None or atr_value <= 0:
            continue
        previous_high = max(item.high for item in candles[index - lookback : index])
        if candle.close <= previous_high:
            continue
        entry = candle.close
        stop = entry - _decimal(atr_multiple) * _decimal(atr_value)
        signals.append(
            Signal(
                market=candle.market,
                symbol=candle.symbol,
                timeframe=candle.timeframe,
                strategy_id="t1_donchian",
                strategy_version=strategy_version,
                side=OrderSide.BUY,
                entry_ref=entry,
                stop=stop,
                bar_ts_utc=candle.ts_open_utc,
                created_ts=created_ts,
            )
        )
    return signals


def t4_rsi_pullback(
    candles: Sequence[Candle],
    sma_values: Sequence[float | None],
    rsi_values: Sequence[float | None],
    atr_values: Sequence[float | None],
    *,
    rsi_threshold: float = 10.0,
    atr_multiple: float = 2.5,
    strategy_version: str = "1.0.0",
    created_ts: datetime,
) -> list[Signal]:
    """Emit T4 entries when price is above SMA and RSI is oversold."""
    if rsi_threshold <= 0 or atr_multiple <= 0:
        raise ValueError("rsi_threshold and atr_multiple must be positive")
    if not (len(candles) == len(sma_values) == len(rsi_values) == len(atr_values)):
        raise ValueError("candles and indicator values must have equal lengths")
    signals: list[Signal] = []
    for candle, sma_value, rsi_value, atr_value in zip(
        candles, sma_values, rsi_values, atr_values, strict=True
    ):
        if sma_value is None or rsi_value is None or atr_value is None or atr_value <= 0:
            continue
        if float(candle.close) <= sma_value or rsi_value >= rsi_threshold:
            continue
        entry = candle.close
        stop = entry - _decimal(atr_multiple) * _decimal(atr_value)
        signals.append(
            Signal(
                market=candle.market,
                symbol=candle.symbol,
                timeframe=candle.timeframe,
                strategy_id="t4_rsi_pullback",
                strategy_version=strategy_version,
                side=OrderSide.BUY,
                entry_ref=entry,
                stop=stop,
                bar_ts_utc=candle.ts_open_utc,
                created_ts=created_ts,
            )
        )
    return signals
