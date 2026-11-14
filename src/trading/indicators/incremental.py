"""Stateful indicator updates for live candle streams.

Each update consumes one closed value and returns the same value the matching
batch indicator would produce at that index.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass
class SMAState:
    period: int
    _values: deque[float] = field(default_factory=deque, init=False)
    _total: float = field(default=0.0, init=False)

    def __post_init__(self) -> None:
        if self.period <= 0:
            raise ValueError("period must be positive")

    def update(self, value: float) -> float | None:
        self._values.append(value)
        self._total += value
        if len(self._values) > self.period:
            self._total -= self._values.popleft()
        return self._total / self.period if len(self._values) == self.period else None


@dataclass
class EMAState:
    period: int
    _sma: SMAState = field(init=False)
    _current: float | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.period <= 0:
            raise ValueError("period must be positive")
        self._sma = SMAState(self.period)

    def update(self, value: float) -> float | None:
        if self._current is None:
            seed = self._sma.update(value)
            if seed is None:
                return None
            self._current = seed
            return seed
        alpha = 2.0 / (self.period + 1)
        self._current = alpha * value + (1.0 - alpha) * self._current
        return self._current


@dataclass
class RSIState:
    period: int
    _previous: float | None = field(default=None, init=False)
    _gains: list[float] = field(default_factory=list, init=False)
    _losses: list[float] = field(default_factory=list, init=False)
    _avg_gain: float | None = field(default=None, init=False)
    _avg_loss: float | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.period <= 0:
            raise ValueError("period must be positive")

    def update(self, value: float) -> float | None:
        if self._previous is None:
            self._previous = value
            return None
        change = value - self._previous
        self._previous = value
        gain, loss = max(change, 0.0), max(-change, 0.0)
        if self._avg_gain is None or self._avg_loss is None:
            self._gains.append(gain)
            self._losses.append(loss)
            if len(self._gains) < self.period:
                return None
            self._avg_gain = sum(self._gains) / self.period
            self._avg_loss = sum(self._losses) / self.period
        else:
            self._avg_gain = (self._avg_gain * (self.period - 1) + gain) / self.period
            self._avg_loss = (self._avg_loss * (self.period - 1) + loss) / self.period
        if self._avg_loss == 0:
            return 50.0 if self._avg_gain == 0 else 100.0
        return 100.0 - 100.0 / (1.0 + self._avg_gain / self._avg_loss)


@dataclass
class ATRState:
    period: int
    _previous_close: float | None = field(default=None, init=False)
    _ranges: list[float] = field(default_factory=list, init=False)
    _current: float | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.period <= 0:
            raise ValueError("period must be positive")

    def update(self, high: float, low: float, close: float) -> float | None:
        if self._previous_close is None:
            self._previous_close = close
            return None
        true_range = max(
            high - low,
            abs(high - self._previous_close),
            abs(low - self._previous_close),
        )
        self._previous_close = close
        if self._current is None:
            self._ranges.append(true_range)
            if len(self._ranges) < self.period:
                return None
            self._current = sum(self._ranges) / self.period
        else:
            self._current = (self._current * (self.period - 1) + true_range) / self.period
        return self._current


@dataclass
class BollingerState:
    period: int
    deviations: float
    _values: deque[float] = field(default_factory=deque, init=False)

    def __post_init__(self) -> None:
        if self.period <= 0 or self.deviations < 0:
            raise ValueError("period must be positive and deviations non-negative")

    def update(self, value: float) -> tuple[float, float, float] | None:
        self._values.append(value)
        if len(self._values) > self.period:
            self._values.popleft()
        if len(self._values) < self.period:
            return None
        mean = sum(self._values) / self.period
        variance = sum((item - mean) ** 2 for item in self._values) / self.period
        spread = variance**0.5 * self.deviations
        return mean, mean - spread, mean + spread


@dataclass
class DonchianState:
    period: int
    _highs: deque[float] = field(default_factory=deque, init=False)
    _lows: deque[float] = field(default_factory=deque, init=False)

    def __post_init__(self) -> None:
        if self.period <= 0:
            raise ValueError("period must be positive")

    def update(self, high: float, low: float) -> tuple[float, float] | None:
        channel = None
        if len(self._highs) == self.period:
            channel = max(self._highs), min(self._lows)
        self._highs.append(high)
        self._lows.append(low)
        if len(self._highs) > self.period:
            self._highs.popleft()
            self._lows.popleft()
        return channel


@dataclass
class VWAPState:
    period: int | None = None
    _values: deque[tuple[float, float]] = field(default_factory=deque, init=False)

    def __post_init__(self) -> None:
        if self.period is not None and self.period <= 0:
            raise ValueError("period must be positive")

    def update(self, high: float, low: float, close: float, volume: float) -> float | None:
        if volume < 0:
            raise ValueError("volume must be non-negative")
        self._values.append(((high + low + close) / 3.0, volume))
        if self.period is not None and len(self._values) > self.period:
            self._values.popleft()
        total_volume = sum(item[1] for item in self._values)
        if total_volume == 0:
            return None
        return sum(price * volume for price, volume in self._values) / total_volume


@dataclass
class ADXState:
    period: int
    _previous: tuple[float, float, float] | None = field(default=None, init=False)
    _tr_values: list[float] = field(default_factory=list, init=False)
    _plus_values: list[float] = field(default_factory=list, init=False)
    _minus_values: list[float] = field(default_factory=list, init=False)
    _tr_avg: float | None = field(default=None, init=False)
    _plus_avg: float | None = field(default=None, init=False)
    _minus_avg: float | None = field(default=None, init=False)
    _dx_values: list[float] = field(default_factory=list, init=False)
    _adx: float | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.period <= 0:
            raise ValueError("period must be positive")

    def update(self, high: float, low: float, close: float) -> float | None:
        if self._previous is None:
            self._previous = (high, low, close)
            return None
        previous_high, previous_low, previous_close = self._previous
        self._previous = (high, low, close)
        tr = max(high - low, abs(high - previous_close), abs(low - previous_close))
        up = high - previous_high
        down = previous_low - low
        plus = up if up > down and up > 0 else 0.0
        minus = down if down > up and down > 0 else 0.0
        if self._tr_avg is None:
            self._tr_values.append(tr)
            self._plus_values.append(plus)
            self._minus_values.append(minus)
            if len(self._tr_values) < self.period:
                return None
            self._tr_avg = sum(self._tr_values) / self.period
            self._plus_avg = sum(self._plus_values) / self.period
            self._minus_avg = sum(self._minus_values) / self.period
        else:
            assert self._plus_avg is not None and self._minus_avg is not None
            self._tr_avg = (self._tr_avg * (self.period - 1) + tr) / self.period
            self._plus_avg = (self._plus_avg * (self.period - 1) + plus) / self.period
            self._minus_avg = (self._minus_avg * (self.period - 1) + minus) / self.period
        assert self._plus_avg is not None and self._minus_avg is not None
        plus_di = 100.0 * self._plus_avg / self._tr_avg if self._tr_avg else 0.0
        minus_di = 100.0 * self._minus_avg / self._tr_avg if self._tr_avg else 0.0
        denominator = plus_di + minus_di
        dx = 0.0 if denominator == 0 else 100.0 * abs(plus_di - minus_di) / denominator
        if self._adx is None:
            self._dx_values.append(dx)
            if len(self._dx_values) < self.period:
                return None
            self._adx = sum(self._dx_values) / self.period
        else:
            self._adx = (self._adx * (self.period - 1) + dx) / self.period
        return self._adx
