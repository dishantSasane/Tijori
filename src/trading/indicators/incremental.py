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
