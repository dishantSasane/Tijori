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
