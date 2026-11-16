"""Point-in-time crypto symbol/listing integrity registry.

Crypto has no splits or dividends (AGENTS.md crypto note), but it has an
equivalent data-integrity problem: exchanges delist tokens, tickers get
rebranded (new contract, same project), and a symbol can be re-used later for
an unrelated token. Treating "BTCUSDT" as one continuous identity forever is
how survivorship bias and silent symbol collisions creep into backtests.

This module is the crypto counterpart of
`trading.storage.corporate_actions`: a validated, point-in-time registry of
listing spans per symbol, with a known-answer detector for gaps that look
like an undeclared delisting/rebrand rather than a mere exchange outage.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from trading.core.enums import MarketId
from trading.core.models import Contract

ListingEventKind = Literal["listed", "delisted", "rebranded"]


class ListingEvent(Contract):
    """One sourced listing-status change for a symbol on one exchange."""

    event_id: str = Field(min_length=1)
    market: MarketId
    exchange: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    kind: ListingEventKind
    effective_date: date
    source_ref: str = Field(min_length=1)
    #: For "rebranded" events: the new symbol this identity continues under.
    successor_symbol: str | None = None

    @model_validator(mode="after")
    def _rebrand_requires_successor(self) -> ListingEvent:
        if self.market not in (MarketId.CRYPTO, MarketId.MEMECOIN):
            raise ValueError("crypto integrity registry supports CRYPTO/MEMECOIN only")
        if self.kind == "rebranded" and not self.successor_symbol:
            raise ValueError("a rebranded event must name a successor_symbol")
        if self.kind != "rebranded" and self.successor_symbol is not None:
            raise ValueError("only rebranded events may carry a successor_symbol")
        return self


class ListingRegistry(Contract):
    """Ordered listing events for one exchange; builds per-symbol spans."""

    exchange: str = Field(min_length=1)
    events: tuple[ListingEvent, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_event_sequence(self) -> ListingRegistry:
        seen_ids: set[str] = set()
        by_symbol: dict[str, list[ListingEvent]] = defaultdict(list)
        for event in self.events:
            if event.exchange != self.exchange:
                raise ValueError(f"event exchange {event.exchange} != registry {self.exchange}")
            if event.event_id in seen_ids:
                raise ValueError(f"duplicate listing event id: {event.event_id}")
            seen_ids.add(event.event_id)
            by_symbol[event.symbol].append(event)

        for symbol, symbol_events in by_symbol.items():
            ordered = sorted(symbol_events, key=lambda event: event.effective_date)
            state: ListingEventKind | None = None
            for event in ordered:
                if event.kind == "listed":
                    if state in ("listed",):
                        raise ValueError(f"{symbol}: duplicate 'listed' without a prior close")
                elif state != "listed":
                    raise ValueError(
                        f"{symbol}: {event.kind} event with no open 'listed' span before it"
                    )
                state = event.kind
        return self

    def is_tradeable(self, symbol: str, as_of: date) -> bool:
        """Whether `symbol` is in an open ("listed") span on `as_of`."""
        symbol_events = sorted(
            (event for event in self.events if event.symbol == symbol),
            key=lambda event: event.effective_date,
        )
        open_span = False
        for event in symbol_events:
            if event.effective_date > as_of:
                break
            open_span = event.kind == "listed"
        return open_span

    def flag_undeclared_gaps(
        self, symbol: str, candle_dates: list[date], *, max_gap_days: int = 3
    ) -> list[tuple[date, date]]:
        """Flag candle-date gaps wider than `max_gap_days` with no matching
        delisted/rebranded event covering the gap -- these look like a silent
        delisting the registry hasn't caught up with yet, and must fail the
        ingestion closed rather than be averaged over.
        """
        ordered_dates = sorted(candle_dates)
        covered_gap_dates = {
            event.effective_date
            for event in self.events
            if event.symbol == symbol and event.kind in ("delisted", "rebranded")
        }
        flagged: list[tuple[date, date]] = []
        for earlier, later in zip(ordered_dates, ordered_dates[1:], strict=False):
            gap_days = (later - earlier).days
            if gap_days > max_gap_days and not covered_gap_dates & {earlier, later}:
                flagged.append((earlier, later))
        return flagged
