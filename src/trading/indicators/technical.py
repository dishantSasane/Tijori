"""Pure technical indicators with explicit warm-up periods."""

from __future__ import annotations

from collections.abc import Sequence
from math import sqrt


def _period(period: int) -> None:
    if period <= 0:
        raise ValueError("period must be positive")


def _wilder(values: Sequence[float | None], period: int) -> list[float | None]:
    """Wilder-smooth a series whose first ``period`` values are available."""
    result: list[float | None] = [None] * len(values)
    first = next((i for i, value in enumerate(values) if value is not None), None)
    if first is None or len(values) - first < period:
        return result
    seed_end = first + period
    if any(value is None for value in values[first:seed_end]):
        return result
    current = sum(float(value) for value in values[first:seed_end] if value is not None) / period
    result[seed_end - 1] = current
    for index in range(seed_end, len(values)):
        value = values[index]
        if value is None:
            continue
        current = (current * (period - 1) + float(value)) / period
        result[index] = current
    return result


def rsi(values: Sequence[float], period: int) -> list[float | None]:
    """Return Wilder RSI, seeded from the first ``period`` changes."""
    _period(period)
    gains: list[float | None] = [None]
    losses: list[float | None] = [None]
    for previous, current in zip(values, values[1:], strict=False):
        change = current - previous
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain = _wilder(gains, period)
    avg_loss = _wilder(losses, period)
    result: list[float | None] = [None] * len(values)
    for index, (gain, loss) in enumerate(zip(avg_gain, avg_loss, strict=False)):
        if gain is None or loss is None:
            continue
        if loss == 0:
            result[index] = 50.0 if gain == 0 else 100.0
        else:
            result[index] = 100.0 - (100.0 / (1.0 + gain / loss))
    return result


def atr(
    highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int
) -> list[float | None]:
    """Return Wilder ATR; the first true range needs the previous close."""
    _period(period)
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("highs, lows, and closes must have equal lengths")
    true_ranges: list[float | None] = [None]
    for index in range(1, len(closes)):
        true_ranges.append(
            max(
                highs[index] - lows[index],
                abs(highs[index] - closes[index - 1]),
                abs(lows[index] - closes[index - 1]),
            )
        )
    return _wilder(true_ranges, period)


def bollinger(
    values: Sequence[float], period: int, deviations: float
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """Return middle, lower, and upper bands using population standard deviation."""
    _period(period)
    if deviations < 0:
        raise ValueError("deviations must be non-negative")
    middle: list[float | None] = [None] * len(values)
    lower: list[float | None] = [None] * len(values)
    upper: list[float | None] = [None] * len(values)
    for index in range(period - 1, len(values)):
        window = values[index - period + 1 : index + 1]
        mean = sum(window) / period
        spread = sqrt(sum((value - mean) ** 2 for value in window) / period)
        middle[index] = mean
        lower[index] = mean - deviations * spread
        upper[index] = mean + deviations * spread
    return middle, lower, upper


def donchian(
    highs: Sequence[float], lows: Sequence[float], period: int
) -> tuple[list[float | None], list[float | None]]:
    """Return previous-window high and low channels (current bar excluded)."""
    _period(period)
    if len(highs) != len(lows):
        raise ValueError("highs and lows must have equal lengths")
    upper: list[float | None] = [None] * len(highs)
    lower: list[float | None] = [None] * len(highs)
    for index in range(period, len(highs)):
        window = slice(index - period, index)
        upper[index] = max(highs[window])
        lower[index] = min(lows[window])
    return upper, lower


def vwap(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    volumes: Sequence[float],
    period: int | None = None,
) -> list[float | None]:
    """Return rolling VWAP of typical prices, or session-style cumulative VWAP.

    A zero-volume window has no meaningful price and therefore returns ``None``.
    """
    if not (len(highs) == len(lows) == len(closes) == len(volumes)):
        raise ValueError("OHLCV inputs must have equal lengths")
    if period is not None:
        _period(period)
    result: list[float | None] = [None] * len(closes)
    for index in range(len(closes)):
        start = 0 if period is None else max(0, index - period + 1)
        weighted = 0.0
        total_volume = 0.0
        for item in range(start, index + 1):
            weighted += ((highs[item] + lows[item] + closes[item]) / 3.0) * volumes[item]
            total_volume += volumes[item]
        if total_volume > 0:
            result[index] = weighted / total_volume
    return result


def adx(
    highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int
) -> list[float | None]:
    """Return Wilder ADX with zero for a flat, directionless market."""
    _period(period)
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("highs, lows, and closes must have equal lengths")
    true_ranges: list[float | None] = [None]
    plus: list[float | None] = [None]
    minus: list[float | None] = [None]
    for index in range(1, len(closes)):
        up_move = highs[index] - highs[index - 1]
        directional_down = lows[index - 1] - lows[index]
        plus.append(up_move if up_move > directional_down and up_move > 0 else 0.0)
        minus.append(
            directional_down if directional_down > up_move and directional_down > 0 else 0.0
        )
        true_ranges.append(
            max(
                highs[index] - lows[index],
                abs(highs[index] - closes[index - 1]),
                abs(lows[index] - closes[index - 1]),
            )
        )
    smoothed_tr = _wilder(true_ranges, period)
    smoothed_plus = _wilder(plus, period)
    smoothed_minus = _wilder(minus, period)
    dx: list[float | None] = [None] * len(closes)
    for index, (tr_value, plus_dm, minus_dm) in enumerate(
        zip(smoothed_tr, smoothed_plus, smoothed_minus, strict=False)
    ):
        if tr_value is None or plus_dm is None or minus_dm is None:
            continue
        plus_di = 100.0 * plus_dm / tr_value if tr_value else 0.0
        minus_di = 100.0 * minus_dm / tr_value if tr_value else 0.0
        denominator = plus_di + minus_di
        dx[index] = 0.0 if denominator == 0 else 100.0 * abs(plus_di - minus_di) / denominator
    return _wilder(dx, period)
