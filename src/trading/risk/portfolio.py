"""Inputs the risk engine's checks read; not yet needed anywhere else, so they
land here with the engine (docs/specs/RISK_ENGINE_SPEC.md §1) rather than in
`core/models.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from trading.core.enums import MarketId, Mode


@dataclass(frozen=True)
class SleeveState:
    """Everything check order needs about one sleeve at decision time."""

    equity: Decimal
    open_positions: int
    daily_pnl_pct: Decimal
    allocation_used_pct: Decimal
    allocation_cap_pct: Decimal
    max_positions: int
    paused_instances: frozenset[str] = field(default_factory=frozenset)
    open_symbols: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class PortfolioState:
    """Snapshot the risk engine consults for one `check()` call. Constructed
    fresh by the caller each time — never mutated in place, never held across
    calls, so `check()` stays a pure function of its inputs (§8).
    """

    sleeves: dict[str, SleeveState]
    total_open_positions: int
    portfolio_peak_equity: Decimal
    portfolio_equity: Decimal
    decided_signal_ids: frozenset[str] = field(default_factory=frozenset)
    liquidity_cap_qty: Decimal | None = None

    def sleeve(self, name: str) -> SleeveState:
        return self.sleeves[name]

    @property
    def drawdown_pct(self) -> Decimal:
        if self.portfolio_peak_equity <= 0:
            return Decimal(0)
        return (
            (self.portfolio_peak_equity - self.portfolio_equity)
            / self.portfolio_peak_equity
            * Decimal(100)
        )


@dataclass(frozen=True)
class RiskConfig:
    """Resolved config for one sleeve/market, assembled by the caller from
    `config/risk.yaml` + `config/markets.yaml` (§1: not yet a shared contract
    across modules, so this stays a dataclass rather than a `Contract`).
    """

    market: MarketId
    sleeve_mode: Mode
    risk_per_trade_pct: Decimal
    max_position_value_pct: Decimal
    max_risk_distance_pct_of_entry: Decimal
    order_price_band_pct: Decimal
    stale_data_seconds: int
    max_portfolio_drawdown_pct: Decimal
    max_daily_loss_pct: Decimal
    lot_size: Decimal = Decimal(1)
    liquidity_cap_qty: Decimal | None = None
    max_open_positions_total: int | None = None
    """Global cap across all sleeves (check 9); None if not configured for
    this deployment -- distinct from the per-sleeve cap (check 8)."""
