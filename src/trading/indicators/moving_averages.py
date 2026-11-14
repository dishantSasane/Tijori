"""Moving-average indicators.

The functions return one value per input observation. ``None`` marks the
warm-up period, which prevents callers from accidentally treating incomplete
indicators as signals.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

Number = float | Decimal


def _validate_period(period: int) -> None:
    if period <= 0:
        raise ValueError("period must be positive")


def sma(values: Sequence[Number], period: int) -> list[float | None]:
    """Return the simple moving average, seeded at the first full window."""
    _validate_period(period)
    result: list[float | None] = [None] * len(values)
    running = 0.0
    for index, value in enumerate(values):
        running += float(value)
        if index >= period:
            running -= float(values[index - period])
        if index >= period - 1:
            result[index] = running / period
    return result


def ema(values: Sequence[Number], period: int) -> list[float | None]:
    """Return an EMA using the SMA of the first full window as its seed."""
    _validate_period(period)
    result: list[float | None] = [None] * len(values)
    if len(values) < period:
        return result
    alpha = 2.0 / (period + 1)
    current = sum(float(value) for value in values[:period]) / period
    result[period - 1] = current
    for index in range(period, len(values)):
        current = (float(values[index]) * alpha) + (current * (1.0 - alpha))
        result[index] = current
    return result
