"""Point-in-time US equity universe: rule-based (data-derived), plus a
separate benchmark-only index membership manifest.

Same shape as `crypto_universe.py`: trading universe membership is a pure
function of a daily liquidity snapshot (top-N by trailing dollar volume),
never a hand-picked list (AGENTS.md §10) -- so it is survivorship-safe by
construction when replayed against historical snapshots. OTC/pink-sheet
symbols are excluded per docs/MARKETS.md §3's Tier B filter.

The S&P 500 membership manifest below is for benchmarking only (comparing
strategy returns against the index), never for universe selection -- using
today's index members to pick a historical universe is exactly the
survivorship bias this module's trading-universe rule avoids. There is no
single free, continuously point-in-time S&P 500 constituent history API;
the free source used is Wikipedia's "List of S&P 500 companies" page, which
maintains a "Selected/Added" and "Removed" changes table sourced from S&P's
own press releases -- free, but community-maintained, not an official S&P
feed. The owner should treat it as a best-effort benchmark reference, not an
audited source, and a handoff/decision note is warranted if higher-fidelity
provenance (SEC filings, a paid index data vendor) is ever needed.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import Field, model_validator

from trading.core.models import Contract

#: Trading universe rule (docs/MARKETS.md §3 Tier B): top-N US equities by
#: trailing dollar volume, above a liquidity floor, OTC excluded.
US_EQUITY_UNIVERSE_TOP_N = 100
US_EQUITY_MIN_DOLLAR_VOLUME_USD = Decimal("5000000")


class USEquitySnapshot(Contract):
    """One symbol's liquidity facts on one day, as reported by Alpaca's asset
    list plus trailing bars (trailing dollar volume = price * volume,
    averaged by the caller over its own chosen window before this call)."""

    symbol: str = Field(min_length=1)
    trailing_dollar_volume_usd: Decimal = Field(ge=0)
    is_otc: bool
    listed_since: date


def us_equity_universe_members(snapshots: list[USEquitySnapshot], *, as_of: date) -> list[str]:
    """Top-N by trailing dollar volume, OTC excluded, above the liquidity floor.

    `as_of` gates which snapshots are eligible (must already be listed) so a
    backtest reconstructing a historical day's universe only sees what was
    knowable by that day.
    """
    eligible = [
        snapshot
        for snapshot in snapshots
        if snapshot.listed_since <= as_of
        and not snapshot.is_otc
        and snapshot.trailing_dollar_volume_usd >= US_EQUITY_MIN_DOLLAR_VOLUME_USD
    ]
    ranked = sorted(eligible, key=lambda s: s.trailing_dollar_volume_usd, reverse=True)
    return sorted(s.symbol for s in ranked[:US_EQUITY_UNIVERSE_TOP_N])


class SP500MembershipInterval(Contract):
    """One historical S&P 500 membership span, for benchmarking only.

    Source: Wikipedia "List of S&P 500 companies" change log (free, publicly
    editable -- not an official S&P data feed; see module docstring).
    """

    symbol: str = Field(min_length=1)
    company_name_at_time: str = Field(min_length=1)
    effective_from: date
    effective_to: date | None = None
    source_ref: str = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_span(self) -> SP500MembershipInterval:
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to must not precede effective_from")
        return self


def sp500_benchmark_members(intervals: list[SP500MembershipInterval], *, as_of: date) -> list[str]:
    """Symbols whose membership span covers `as_of`. Benchmarking only --
    never feed this into universe selection for live/paper strategies.
    """
    return sorted(
        {
            interval.symbol
            for interval in intervals
            if interval.effective_from <= as_of
            and (interval.effective_to is None or as_of <= interval.effective_to)
        }
    )
