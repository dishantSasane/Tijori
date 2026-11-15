"""Point-in-time crypto sleeve and memecoin sleeve membership.

Both rules are pure functions of a daily liquidity snapshot, never a
hand-picked token list (AGENTS.md §10, DATA_ECOSYSTEM_BUILD_PLAN.md item 3):
membership on any given day only looks at data available by that day, so
re-running this against a historical snapshot reproduces the same universe
survivorship-safely (no "whatever's popular today" leakage).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import Field

from trading.core.models import Contract

#: General crypto sleeve (docs/MARKETS.md §4): BTC/ETH always in, plus the
#: top-N by 24h quote volume above a liquidity floor.
CRYPTO_SLEEVE_TOP_N = 20
CRYPTO_SLEEVE_MIN_QUOTE_VOLUME_USD = Decimal("5000000")
CRYPTO_SLEEVE_ALWAYS_INCLUDE = frozenset({"BTCUSDT", "ETHUSDT"})

#: Memecoin sleeve: objective, mechanical, deliberately stricter than the
#: general sleeve (new tokens are the highest-risk part of this system).
MEMECOIN_MIN_QUOTE_VOLUME_USD = Decimal("1000000")
MEMECOIN_MIN_LISTING_AGE_DAYS = 30


class SymbolSnapshot(Contract):
    """One symbol's liquidity facts on one day, as reported by the exchange."""

    symbol: str = Field(min_length=1)
    quote_volume_24h_usd: Decimal = Field(ge=0)
    listed_since: date
    is_memecoin_tagged: bool


def crypto_sleeve_members(snapshots: list[SymbolSnapshot], *, as_of: date) -> list[str]:
    """Top-N by liquidity above the floor, BTC/ETH always included.

    `as_of` is accepted (and snapshots are expected to be dated no later than
    it) purely so a backtest can reconstruct a historical day's universe
    rather than today's -- this function does not otherwise use it.
    """
    eligible = [
        snapshot
        for snapshot in snapshots
        if snapshot.listed_since <= as_of
        and snapshot.quote_volume_24h_usd >= CRYPTO_SLEEVE_MIN_QUOTE_VOLUME_USD
        and not snapshot.is_memecoin_tagged
    ]
    ranked = sorted(eligible, key=lambda s: s.quote_volume_24h_usd, reverse=True)
    members = {snapshot.symbol for snapshot in ranked[:CRYPTO_SLEEVE_TOP_N]}
    members |= CRYPTO_SLEEVE_ALWAYS_INCLUDE & {snapshot.symbol for snapshot in snapshots}
    return sorted(members)


def memecoin_sleeve_members(snapshots: list[SymbolSnapshot], *, as_of: date) -> list[str]:
    """Mechanical inclusion: tagged as memecoin, liquid enough, old enough."""
    return sorted(
        snapshot.symbol
        for snapshot in snapshots
        if snapshot.is_memecoin_tagged
        and snapshot.listed_since <= as_of
        and (as_of - snapshot.listed_since).days >= MEMECOIN_MIN_LISTING_AGE_DAYS
        and snapshot.quote_volume_24h_usd >= MEMECOIN_MIN_QUOTE_VOLUME_USD
    )
