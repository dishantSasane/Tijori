"""Strategy *instances* for the crypto and US-equity sleeves (P5).

An "instance" is a strategy + market + symbol + timeframe + parameters — not
new strategy math. The signal rules already live in `phase1.py` (T1 Donchian
breakout, T4 RSI pullback) and are market-agnostic: they only read `Candle`/
indicator values, never a market-specific branch. P5's job is to *configure*
them against crypto/US symbols and their `MarketProfile`, the same way P1
configured them against NSE symbols.

T2 and a dedicated "momentum" rule from `docs/BUILD_ORDER.md`'s P5 line are
not implemented anywhere on `main` yet (they live in the strategy-library
work on open, unmerged PR #53 / `codex/p1-build`). Rather than block on that
or re-derive new strategy math here (which would duplicate PR #53 and risk
diverging from whatever it lands with), this module scopes down to the two
rules that exist today: `t1_donchian` (a breakout/momentum rule) and
`t4_rsi_pullback`. Extending `STRATEGY_ID -> callable` below is how T2/true
momentum get added once that PR merges — see `docs/decisions.md` ADR-0033.
"""

from __future__ import annotations

from dataclasses import dataclass

from trading.core.enums import MarketId, Timeframe


@dataclass(frozen=True)
class StrategyInstance:
    """One running (strategy, market, symbol, timeframe) combination."""

    strategy_id: str
    market: MarketId
    symbol: str
    timeframe: Timeframe
    sleeve: str
    strategy_version: str = "1.0.0"


#: Tier-A crypto universe per docs/MARKETS.md §4 (BTC, ETH; "top ~20 by
#: volume" is Tier B scanner work, not in scope here — same scoping call P4
#: made for its ranking placeholder).
CRYPTO_TIER_A = ("BTC/USDT", "ETH/USDT")

#: Tier-A US universe per docs/MARKETS.md §3: a handful of Nasdaq-100 names
#: + key ETFs, not the full 100 — paper-only v1, keep it small and legible.
US_TIER_A = ("AAPL", "MSFT", "QQQ")


def crypto_instances() -> list[StrategyInstance]:
    """T1 breakout + T4 pullback on daily crypto candles. Daily, not
    intraday: crypto is 24/7 (`MarketProfile.is_24x7`), so "daily" here means
    the configured `daily_cutoff_utc` bar, not an exchange session close.
    """
    instances: list[StrategyInstance] = []
    for symbol in CRYPTO_TIER_A:
        instances.append(
            StrategyInstance(
                strategy_id="t1_donchian",
                market=MarketId.CRYPTO,
                symbol=symbol,
                timeframe=Timeframe.D1,
                sleeve="crypto",
            )
        )
        instances.append(
            StrategyInstance(
                strategy_id="t4_rsi_pullback",
                market=MarketId.CRYPTO,
                symbol=symbol,
                timeframe=Timeframe.D1,
                sleeve="crypto",
            )
        )
    return instances


def us_equity_instances() -> list[StrategyInstance]:
    """T1 breakout + T4 pullback on daily US-equity candles (Alpaca free
    plan's IEX feed is daily/EOD-friendly; no intraday US wiring in this PR).
    """
    instances: list[StrategyInstance] = []
    for symbol in US_TIER_A:
        instances.append(
            StrategyInstance(
                strategy_id="t1_donchian",
                market=MarketId.US_EQUITY,
                symbol=symbol,
                timeframe=Timeframe.D1,
                sleeve="us_equity",
            )
        )
        instances.append(
            StrategyInstance(
                strategy_id="t4_rsi_pullback",
                market=MarketId.US_EQUITY,
                symbol=symbol,
                timeframe=Timeframe.D1,
                sleeve="us_equity",
            )
        )
    return instances
