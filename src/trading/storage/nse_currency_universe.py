"""NSE currency-derivatives coverage: fixed instrument list + session hours.

Verified against Upstox's public API docs and NSE's currency-derivatives
contract specifications (see docs/BUILD_ORDER.md, "NSE currencies coverage"):

- Segment is CDS (exchange code "CDS", segment "CD" in Upstox's instrument
  master), distinct from NSE equity ("NSE_EQ"). Instrument keys follow the
  same ``EXCHANGE|token`` shape the existing UpstoxHistoryClient already
  accepts verbatim — no new HTTP client needed, only correct key strings.
- Session hours are 09:00-17:00 IST, NOT the equity 09:15-15:30 window
  docs/MARKETS.md flagged as unverified.
- Currency futures expire monthly and are cash-settled. Unlike MCX, this
  module makes NO attempt at a continuous/stitched series: each expiry is
  a separate instrument_key queried on its own. There is no "fake price
  jump" risk because nothing is stitched — so no roll-adjustment layer is
  needed here (contrast with MCX, which may need one in phase 4).
- No corporate-action equivalent exists for an FX future (no split/dividend),
  so no integrity/adjustment layer is needed either.
"""

from __future__ import annotations

from dataclasses import dataclass

from trading.core.enums import MarketId

#: NSE currency-derivatives session, IST. Verified against NSE's currency
#: derivatives contract specifications; differs from NSE equity (09:15-15:30).
SESSION_START_IST = "09:00"
SESSION_END_IST = "17:00"


@dataclass(frozen=True)
class CurrencyPair:
    """One fixed, hand-enumerated currency-derivatives underlying.

    Deliberately not a liquidity-rule universe (AGENTS.md §10 keeps this
    sleeve small) -- just the four tenors docs/MARKETS.md names.
    """

    symbol: str
    instrument_key_prefix: str
    market: MarketId = MarketId.NSE_CURRENCY


#: Fixed, tiny universe. Each entry is the underlying; a specific tradeable
#: instrument_key also needs an expiry suffix from Upstox's instrument
#: master (not hardcoded here since expiries roll monthly).
CURRENCY_UNIVERSE: tuple[CurrencyPair, ...] = (
    CurrencyPair(symbol="USDINR", instrument_key_prefix="CDS_FO|USDINR"),
    CurrencyPair(symbol="EURINR", instrument_key_prefix="CDS_FO|EURINR"),
    CurrencyPair(symbol="GBPINR", instrument_key_prefix="CDS_FO|GBPINR"),
    CurrencyPair(symbol="JPYINR", instrument_key_prefix="CDS_FO|JPYINR"),
)


def symbols() -> tuple[str, ...]:
    """Point-in-time universe is static: these four tenors, always."""
    return tuple(pair.symbol for pair in CURRENCY_UNIVERSE)
