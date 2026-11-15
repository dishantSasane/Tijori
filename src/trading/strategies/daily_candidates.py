"""Daily P1 candidate entry rules whose indicators are computed upstream."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from decimal import Decimal
from math import isfinite

from trading.core.enums import OrderSide, Timeframe
from trading.core.models import Candle, Signal
from trading.strategies.p1_catalog import get_p1_candidate
from trading.strategies.phase1 import t1_exit_trigger, t4_exit_trigger


def _validate_inputs(candles: Sequence[Candle], *series: Sequence[float | None]) -> None:
    if any(len(candles) != len(values) for values in series):
        raise ValueError("candles and indicator values must have equal lengths")
    if any(value is not None and not isfinite(value) for values in series for value in values):
        raise ValueError("indicator values must be finite or None")


def _make_long_signal(
    candle: Candle,
    *,
    strategy_id: str,
    strategy_version: str,
    atr_value: float,
    atr_multiple: float,
    created_ts: datetime,
) -> Signal | None:
    stop = candle.close - Decimal(str(atr_multiple)) * Decimal(str(atr_value))
    if stop <= 0:
        return None
    return Signal(
        market=candle.market,
        symbol=candle.symbol,
        timeframe=candle.timeframe,
        strategy_id=strategy_id,
        strategy_version=strategy_version,
        side=OrderSide.BUY,
        entry_ref=candle.close,
        stop=stop,
        bar_ts_utc=candle.ts_open_utc,
        created_ts=created_ts,
    )


def t2_ema_adx(
    candles: Sequence[Candle],
    fast_ema: Sequence[float | None],
    slow_ema: Sequence[float | None],
    adx_values: Sequence[float | None],
    atr_values: Sequence[float | None],
    *,
    adx_threshold: float = 25.0,
    atr_multiple: float = 2.0,
    strategy_version: str = "1.0.0",
    created_ts: datetime,
) -> list[Signal]:
    """Emit T2 long entries on a bullish EMA crossover with sufficient ADX.

    The caller selects EMA(20)/EMA(50) by default or one of the two other
    frozen crossover pairs in `P1_CANDIDATES.md`. Indicators at index ``i``
    use closed bars through ``i`` only. Fills are delegated to the shared
    next-open backtest path.
    """
    if not isfinite(adx_threshold) or adx_threshold <= 0:
        raise ValueError("adx_threshold must be finite and positive")
    if not isfinite(atr_multiple) or atr_multiple <= 0:
        raise ValueError("atr_multiple must be finite and positive")
    _validate_inputs(candles, fast_ema, slow_ema, adx_values, atr_values)
    signals: list[Signal] = []
    for index in range(1, len(candles)):
        prior_fast, prior_slow = fast_ema[index - 1], slow_ema[index - 1]
        fast, slow = fast_ema[index], slow_ema[index]
        adx_value, atr_value = adx_values[index], atr_values[index]
        if None in (prior_fast, prior_slow, fast, slow, adx_value, atr_value):
            continue
        assert prior_fast is not None and prior_slow is not None
        assert fast is not None and slow is not None
        assert adx_value is not None and atr_value is not None
        if prior_fast > prior_slow or fast <= slow or adx_value <= adx_threshold or atr_value <= 0:
            continue
        signal = _make_long_signal(
            candles[index],
            strategy_id="t2_ema_adx",
            strategy_version=strategy_version,
            atr_value=atr_value,
            atr_multiple=atr_multiple,
            created_ts=created_ts,
        )
        if signal is not None:
            signals.append(signal)
    return signals


def t2_exit_trigger(*, fast_ema: float | None, slow_ema: float | None) -> bool:
    """Return T2's closed-bar bearish crossover exit condition."""
    return fast_ema is not None and slow_ema is not None and fast_ema < slow_ema


def t6_bollinger_reversion(
    candles: Sequence[Candle],
    lower_band: Sequence[float | None],
    middle_band: Sequence[float | None],
    adx_values: Sequence[float | None],
    atr_values: Sequence[float | None],
    *,
    adx_maximum: float = 20.0,
    atr_multiple: float = 1.5,
    strategy_version: str = "1.0.0",
    created_ts: datetime,
) -> list[Signal]:
    """Emit T6 long entries below the lower band in a low-ADX regime.

    `middle_band` is accepted and length-validated for the matching T6 exit
    rule, which is evaluated by the caller on closed bars.
    """
    if not isfinite(adx_maximum) or adx_maximum <= 0:
        raise ValueError("adx_maximum must be finite and positive")
    if not isfinite(atr_multiple) or atr_multiple <= 0:
        raise ValueError("atr_multiple must be finite and positive")
    _validate_inputs(candles, lower_band, middle_band, adx_values, atr_values)
    signals: list[Signal] = []
    for index, candle in enumerate(candles):
        lower, adx_value, atr_value = lower_band[index], adx_values[index], atr_values[index]
        if lower is None or adx_value is None or atr_value is None:
            continue
        if candle.close >= Decimal(str(lower)) or adx_value >= adx_maximum or atr_value <= 0:
            continue
        signal = _make_long_signal(
            candle,
            strategy_id="t6_bollinger_reversion",
            strategy_version=strategy_version,
            atr_value=atr_value,
            atr_multiple=atr_multiple,
            created_ts=created_ts,
        )
        if signal is not None:
            signals.append(signal)
    return signals


def t6_exit_trigger(*, close: Decimal, middle_band: float | Decimal | None, bars_held: int) -> bool:
    """Return T6's middle-band or time-stop condition on a closed bar."""
    if bars_held < 0:
        raise ValueError("bars_held must be non-negative")
    return bars_held >= 10 or (middle_band is not None and close >= Decimal(str(middle_band)))


def make_daily_exit_condition(
    candidate_id: str,
    candles: Sequence[Candle],
    *,
    fast_ema: Sequence[float | None] | None = None,
    slow_ema: Sequence[float | None] | None = None,
    sma5: Sequence[float | None] | None = None,
    rsi_values: Sequence[float | None] | None = None,
    middle_band: Sequence[float | None] | None = None,
) -> Callable[[Signal, int, Candle], bool]:
    """Build the frozen candidate exit callback for ``run_long_only``.

    Indicator arrays must be aligned to the supplied candles and must contain
    only values computed from bars closed through that index. Stop checks stay
    in the shared runner and take precedence over this close-based callback.
    """
    candidate = get_p1_candidate(candidate_id)
    if candidate.timeframe != Timeframe.D1.value:
        raise ValueError("daily exit callback requires a daily P1 candidate")
    series = {
        "fast_ema": fast_ema,
        "slow_ema": slow_ema,
        "sma5": sma5,
        "rsi_values": rsi_values,
        "middle_band": middle_band,
    }
    for name, values in series.items():
        if values is not None and len(values) != len(candles):
            raise ValueError(f"{name} must align with candles")
        if values is not None and any(
            value is not None and not isfinite(value) for value in values
        ):
            raise ValueError(f"{name} must contain finite values or None")

    if candidate.family == "T2" and (fast_ema is None or slow_ema is None):
        raise ValueError("T2 exits require fast_ema and slow_ema")
    if candidate.family == "T4" and (sma5 is None or rsi_values is None):
        raise ValueError("T4 exits require sma5 and rsi_values")
    if candidate.family == "T6" and middle_band is None:
        raise ValueError("T6 exits require middle_band")

    entry_indices = {bar.ts_open_utc: index + 1 for index, bar in enumerate(candles)}
    parameters = dict(candidate.parameters)

    def should_exit(signal: Signal, index: int, candle: Candle) -> bool:
        if candle.timeframe is not Timeframe.D1 or not 0 <= index < len(candles):
            raise ValueError("daily exit callback received an invalid candle index")
        if candles[index].ts_open_utc != candle.ts_open_utc:
            raise ValueError("daily exit callback candle does not match its input series")
        if signal.bar_ts_utc not in entry_indices:
            raise ValueError("signal bar is absent from the exit callback candle series")
        bars_held = index - entry_indices[signal.bar_ts_utc] + 1
        if bars_held <= 0:
            return False

        if candidate.family == "T1":
            lookback = int(parameters["exit_m"])
            if index < lookback:
                return False
            lows = [bar.low for bar in candles[index - lookback : index]]
            return t1_exit_trigger(close=candle.close, prior_lows=lows, exit_lookback=lookback)
        if candidate.family == "T2":
            assert fast_ema is not None and slow_ema is not None
            return t2_exit_trigger(fast_ema=fast_ema[index], slow_ema=slow_ema[index])
        if candidate.family == "T4":
            assert sma5 is not None and rsi_values is not None
            return t4_exit_trigger(
                close=candle.close,
                sma5=sma5[index],
                rsi=rsi_values[index],
                bars_held=bars_held,
            )
        assert candidate.family == "T6" and middle_band is not None
        return t6_exit_trigger(
            close=candle.close,
            middle_band=middle_band[index],
            bars_held=bars_held,
        )

    return should_exit
