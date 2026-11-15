"""Cross-symbol session-coverage audit for the P1 five-symbol pilot.

BUILD_ORDER.md's P1a deliverable: "audit the five archived daily series for
session gaps ... report incomplete or uncertain sessions rather than
filling/dropping silently." Automated NSE calendar scraping is owner-
prohibited (docs/DATA_ACCESS.md), so the only immediately permitted check is
cross-symbol consistency: an NSE session one pilot blue-chip traded on should
normally be one every pilot blue-chip traded on (all five are large, liquid,
continuously-listed names across the whole window). Where that's not true,
it's a flag to resolve against a permitted source later (e.g. an NSE special-
session circular, itself a downloadable document, not a scrape target) -- not
something to silently fill, drop, or average away.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class SessionCoverageAudit:
    symbols: tuple[str, ...]
    common_sessions: frozenset[date]
    """Dates every symbol traded on -- the only sessions safe to use for a
    synchronized multi-symbol backtest/bootstrap, per P1_EVALUATION.md's
    "one value per verified exchange session" requirement for the daily
    portfolio-return vector.
    """
    symbol_only_dates: Mapping[str, frozenset[date]]
    """Dates present for this symbol but missing from at least one other
    pilot symbol -- flagged, never silently included in `common_sessions`
    or dropped from the symbol's own raw record.
    """

    @property
    def has_discrepancies(self) -> bool:
        return any(dates for dates in self.symbol_only_dates.values())


def audit_session_coverage(
    dates_by_symbol: Mapping[str, frozenset[date]],
) -> SessionCoverageAudit:
    """Pure function: compare already-loaded per-symbol trading-date sets."""
    if len(dates_by_symbol) < 2:
        raise ValueError("cross-symbol audit needs at least two symbols")
    if any(not dates for dates in dates_by_symbol.values()):
        raise ValueError("every symbol must have at least one session")
    common = frozenset.intersection(*dates_by_symbol.values())
    symbol_only = {symbol: frozenset(dates - common) for symbol, dates in dates_by_symbol.items()}
    return SessionCoverageAudit(
        symbols=tuple(sorted(dates_by_symbol)),
        common_sessions=common,
        symbol_only_dates=symbol_only,
    )


class RawUpstoxArchiveError(ValueError):
    """Raised when an archived raw response isn't a usable success payload."""


def load_raw_upstox_daily_dates(path: Path) -> frozenset[date]:
    """Extract the set of candle dates from one archived raw Upstox V3
    response (the format `upstox_history.py`'s requester returns, before any
    parsing/adjustment -- this reads the preserved raw bytes directly, it
    does not re-fetch or trust a cached parse).
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "success":
        raise RawUpstoxArchiveError(f"{path}: not a successful Upstox response")
    candles = payload.get("data", {}).get("candles")
    if not isinstance(candles, list) or not candles:
        raise RawUpstoxArchiveError(f"{path}: no candles in response")
    return frozenset(datetime.fromisoformat(str(row[0])).date() for row in candles)
