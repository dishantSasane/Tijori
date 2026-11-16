"""Per-market profile: trading hours, costs, and universe knobs that differ by
market (docs/MARKETS.md §8). One `MarketProfile` per `MarketId`, loaded from
`config/markets.yaml` (falls back to the committed `.example.yaml`, same
convention as `core.config.load_yaml`).

This is deliberately thin: it only models what P5 code actually reads
(crypto being 24/7 vs. US/India having an exchange session). Fields the repo
doesn't consume yet (e.g. detailed tax notes) stay as the raw dict under
`extra` rather than being speculatively typed (YAGNI, AGENTS.md §6).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from trading.core.config import load_yaml
from trading.core.enums import MarketId

#: `MarketId` -> top-level key in `config/markets.yaml`. Kept explicit rather
#: than derived from `MarketId.value` because the two don't match everywhere
#: (`MarketId.MCX_COMMODITY` is `mcx_commodity`; the markets-config key,
#: chosen before this enum value existed, is `commodities_mcx`).
_CONFIG_KEY: dict[MarketId, str] = {
    MarketId.IN_EQUITY: "india_equity",
    MarketId.US_EQUITY: "us_equity",
    MarketId.CRYPTO: "crypto",
    MarketId.MCX_COMMODITY: "commodities_mcx",
    MarketId.NSE_CURRENCY: "nse_currency",
    MarketId.MEMECOIN: "memecoin",
}


class MarketProfile(BaseModel):
    """One market's trading-hours/cost profile. `is_24x7=True` means there is
    no exchange session to check before placing a paper order (crypto); the
    scheduler built for session-based markets (`candles/scheduler.py`) must
    not be assumed to apply (see `docs/learn/0005-market-profiles.md`).
    """

    model_config = ConfigDict(frozen=True, extra="allow")

    market: MarketId
    calendar: str
    timezone: str
    is_24x7: bool = False
    session_open: str | None = None
    session_close: str | None = None


def load_market_profile(market: MarketId, config_dir: Path) -> MarketProfile:
    """Load one market's profile out of `config/markets.yaml`."""
    data = load_yaml(config_dir / "markets.yaml")
    key = _CONFIG_KEY.get(market)
    if key is None or key not in data:
        raise KeyError(f"no markets.yaml entry for {market!r} (expected key {key!r})")
    block: dict[str, Any] = data[key]
    session = block.get("session") or {}
    return MarketProfile(
        market=market,
        calendar=block["calendar"],
        timezone=block["timezone"],
        is_24x7=block["calendar"] == "24x7",
        session_open=session.get("open"),
        session_close=session.get("close"),
        **{k: v for k, v in block.items() if k not in {"calendar", "timezone", "session"}},
    )
