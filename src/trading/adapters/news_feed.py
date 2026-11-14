"""NewsFeed Protocol + fake. News text is untrusted input (prompt-injection
risk, AGENTS.md §4.6) — this adapter only fetches; it never reaches the LLM
without going through the Brain's context-building step (P6).
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from trading.core.enums import MarketId


class NewsItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ts_utc: datetime
    source: str
    headline: str
    body: str = ""
    symbols: tuple[str, ...] = ()
    market: MarketId | None = None


class NewsFeed(Protocol):
    def fetch_since(self, since: datetime) -> list[NewsItem]: ...


class FakeNewsFeed:
    def __init__(self, items: list[NewsItem] | None = None) -> None:
        self._items = items or []

    def fetch_since(self, since: datetime) -> list[NewsItem]:
        return [item for item in self._items if item.ts_utc > since]
