"""Continuous-series roll adjustment for MCX commodity futures.

MCX futures expire monthly/bi-monthly, and each expiry is a *different*
instrument_key (same pattern as NSE currencies, docs/BUILD_ORDER.md "NSE
currencies coverage"). Unlike currencies, a continuous MCX series is likely
to be wanted for commodities (real term-structure/carry effects make
single-expiry history short and choppy), so this module builds it -- and is
written generically enough that NSE currencies can reuse it later if a
continuous series is ever wanted there too (flagged in that section).

Method: ratio back-adjustment (a.k.a. "panama" with a multiplicative
factor rather than an additive offset). Multiplicative is used -- not
additive -- because commodity futures can have large relative price swings
(e.g. crude oil) where an additive offset can push old legs' back-adjusted
prices through zero or negative; a ratio cannot.

This produces a *display/backtest* continuous series only. It does not
change what a live strategy sees -- live signal code must still read the
single current-expiry instrument_key directly (AGENTS.md §4.5: no
look-ahead). The adjustment here is applied once, after all legs' candles
are already known, exactly like the corporate-actions adjustment in
``trading.storage.corporate_actions``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from trading.core.models import Candle


class MCXRollError(ValueError):
    """Raised when legs are missing, unordered, or have no overlap to roll at."""


@dataclass(frozen=True)
class ContractLeg:
    """One expiry's raw candle history, in time order."""

    instrument_key: str
    candles: tuple[Candle, ...]


def build_continuous_series(legs: Sequence[ContractLeg]) -> list[Candle]:
    """Stitch successive expiries into one back-adjusted series.

    ``legs`` must be given oldest-expiry-first, each with its own candles
    sorted ascending by ``ts_open_utc``. The roll point between leg i and
    leg i+1 is leg i's last candle and leg i+1's first candle (the caller
    is expected to have already excluded a leg's final illiquid days if
    that matters -- not handled here, AGENTS.md §10 keeps this small).

    Returns every candle from every leg, each carrying its cumulative
    ``adj_factor`` multiplier already applied to open/high/low/close. The
    most recent leg is unadjusted (factor 1); earlier legs are scaled so
    that there is no fake jump at any roll date.
    """
    if not legs:
        raise MCXRollError("no legs given")
    for leg in legs:
        if not leg.candles:
            raise MCXRollError(f"leg {leg.instrument_key} has no candles")
        ts = [c.ts_open_utc for c in leg.candles]
        if ts != sorted(ts):
            raise MCXRollError(f"leg {leg.instrument_key} candles are not time-ordered")

    # Walk legs newest -> oldest. The newest leg is unadjusted (factor 1);
    # each older leg's factor is chosen so its last (raw) close, scaled,
    # equals the next-newer leg's first *adjusted* close -- i.e. no jump
    # across the roll date.
    factors: list[Decimal] = [Decimal("1")] * len(legs)
    for i in range(len(legs) - 2, -1, -1):
        newer, older = legs[i + 1], legs[i]
        newer_first_adjusted_close = newer.candles[0].close * factors[i + 1]
        older_last_raw_close = older.candles[-1].close
        if older_last_raw_close == 0:
            raise MCXRollError(f"leg {older.instrument_key} has a zero close at roll")
        factors[i] = newer_first_adjusted_close / older_last_raw_close

    out: list[Candle] = []
    for leg, factor in zip(legs, factors, strict=True):
        out.extend(_apply_factor(leg.candles, factor))
    return out


def _apply_factor(candles: tuple[Candle, ...], factor: Decimal) -> list[Candle]:
    if factor == Decimal("1"):
        return [c.model_copy(update={"adj_factor": factor}) for c in candles]
    return [
        c.model_copy(
            update={
                "open": c.open * factor,
                "high": c.high * factor,
                "low": c.low * factor,
                "close": c.close * factor,
                "adj_factor": factor,
            }
        )
        for c in candles
    ]
