"""MCX commodities coverage: fixed instrument list.

Verified against Upstox's public instrument master (the daily-refreshed
``MCX.json.gz`` file at
``https://assets.upstox.com/market-quote/instruments/exchange/MCX.json.gz``,
exchange segment ``MCX_FO``) and Upstox's V3 historical-candle API, which is
instrument-key-agnostic (see docs/BUILD_ORDER.md, "MCX commodities
coverage" and src/trading/adapters/upstox_history.py). Same client Codex's
India-equity work and phase 3's NSE-currency work already use -- no new
HTTP client needed, only correct key strings and (unlike currencies) a
roll-adjustment layer, see ``trading.adapters.mcx_roll``.

Fixed, tiny, hand-enumerated universe (AGENTS.md §10 keeps this sleeve
deliberately small) -- the handful of genuinely liquid MCX futures, not a
liquidity-rule-derived universe.
"""

from __future__ import annotations

from dataclasses import dataclass

from trading.core.enums import MarketId


@dataclass(frozen=True)
class MCXCommodity:
    """One fixed, hand-enumerated MCX futures underlying.

    ``instrument_key_prefix`` needs an expiry suffix from Upstox's
    instrument master (not hardcoded here since expiries roll monthly/
    bi-monthly and vary by commodity).
    """

    symbol: str
    instrument_key_prefix: str
    lot_unit: str
    market: MarketId = MarketId.MCX_COMMODITY


#: The commodities MCX itself lists as its most liquid futures contracts.
MCX_UNIVERSE: tuple[MCXCommodity, ...] = (
    MCXCommodity(symbol="GOLD", instrument_key_prefix="MCX_FO|GOLD", lot_unit="10 g"),
    MCXCommodity(symbol="SILVER", instrument_key_prefix="MCX_FO|SILVER", lot_unit="30 kg"),
    MCXCommodity(symbol="CRUDEOIL", instrument_key_prefix="MCX_FO|CRUDEOIL", lot_unit="100 bbl"),
    MCXCommodity(
        symbol="NATURALGAS", instrument_key_prefix="MCX_FO|NATURALGAS", lot_unit="1250 mmBtu"
    ),
    MCXCommodity(symbol="COPPER", instrument_key_prefix="MCX_FO|COPPER", lot_unit="2500 kg"),
)


def symbols() -> tuple[str, ...]:
    """Point-in-time universe is static: these five commodities, always."""
    return tuple(c.symbol for c in MCX_UNIVERSE)
