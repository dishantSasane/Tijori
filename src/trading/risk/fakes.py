"""Fakes for `SessionCalendar`/`DataFreshness`, for tests only. A real calendar
(`exchange_calendars`) and a real `DataFeed`-backed freshness check are P3
work (docs/specs/CANDLE_BUILDER_AND_SCHEDULER_SPEC.md §3.1); the risk engine
only needs the Protocol shape to be implementable against.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal


class FakeSessionCalendar:
    def __init__(self, *, open_markets: set[str] | None = None) -> None:
        self._open_markets = open_markets if open_markets is not None else set()

    def is_open(self, market: str, now: datetime) -> bool:
        return market in self._open_markets

    def set_open(self, market: str, open_: bool) -> None:
        if open_:
            self._open_markets.add(market)
        else:
            self._open_markets.discard(market)


class FakeDataFreshness:
    def __init__(self) -> None:
        self._stale: dict[tuple[str, str], bool] = {}
        self._last_price: dict[tuple[str, str], Decimal] = {}

    def is_stale(self, market: str, symbol: str, now: datetime, max_age_seconds: int) -> bool:
        return self._stale.get((market, symbol), False)

    def last_tick_price(self, market: str, symbol: str) -> Decimal | None:
        return self._last_price.get((market, symbol))

    def set_stale(self, market: str, symbol: str, stale: bool) -> None:
        self._stale[(market, symbol)] = stale

    def set_last_price(self, market: str, symbol: str, price: Decimal) -> None:
        self._last_price[(market, symbol)] = price
