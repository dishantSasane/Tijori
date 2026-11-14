"""DataFeed Protocol + fake. Real adapters (Angel One, Fyers, Alpaca, CCXT) are
built in P1+ against this interface; see docs/MARKETS.md for provider choice.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle, Tick


class DataFeed(Protocol):
    def subscribe(self, market: MarketId, symbol: str, timeframe: Timeframe) -> None:
        """Start streaming/building candles for (market, symbol, timeframe)."""
        ...

    def poll_closed_candles(self) -> list[Candle]:
        """Return and clear any newly-closed candles since the last poll.

        Candles are only ever emitted once closed (AGENTS.md §4.5) — there is
        no "current forming bar" in this interface on purpose.
        """
        ...

    def last_tick(self, market: MarketId, symbol: str) -> Tick | None:
        """Most recent tick seen, or None if nothing has arrived yet."""
        ...

    def is_stale(
        self, market: MarketId, symbol: str, *, as_of: datetime, max_age_seconds: int
    ) -> bool:
        """True if the last tick/candle is older than `max_age_seconds` as of `as_of`
        (docs/RISK_SPEC.md check #4). True (fail closed) if nothing has arrived yet.
        """
        ...


class FakeDataFeed:
    """In-memory fake for tests. Candles are pushed via `push_closed_candle`;
    nothing is generated on a timer.
    """

    def __init__(self) -> None:
        self._pending: list[Candle] = []
        self._last_tick: dict[tuple[MarketId, str], Tick] = {}

    def subscribe(self, market: MarketId, symbol: str, timeframe: Timeframe) -> None:
        pass

    def push_closed_candle(self, candle: Candle) -> None:
        self._pending.append(candle)

    def push_tick(self, tick: Tick) -> None:
        self._last_tick[(tick.market, tick.symbol)] = tick

    def poll_closed_candles(self) -> list[Candle]:
        candles, self._pending = self._pending, []
        return candles

    def last_tick(self, market: MarketId, symbol: str) -> Tick | None:
        return self._last_tick.get((market, symbol))

    def is_stale(
        self, market: MarketId, symbol: str, *, as_of: datetime, max_age_seconds: int
    ) -> bool:
        tick = self.last_tick(market, symbol)
        if tick is None:
            return True
        return (as_of - tick.ts_utc).total_seconds() > max_age_seconds
