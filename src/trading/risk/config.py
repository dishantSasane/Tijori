"""Runtime risk inputs: `PortfolioState` and `RiskConfig`.

docs/specs/RISK_ENGINE_SPEC.md §1 says these become Pydantic contracts only
when the risk engine implementation starts — that's now (P2). They live here,
not in `trading.core.models`, because nothing else consumes them yet (YAGNI
per CONTRACTS.md) and because they carry sleeve/instance runtime state that
is not an immutable "fact" the way a `Signal` or `Fill` is.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SleeveConfig(BaseModel):
    """Per-sleeve limits (docs/RISK_SPEC.md §2, §3)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    risk_per_trade_pct: Decimal = Field(gt=0)
    max_position_value_pct: Decimal = Field(gt=0)
    max_open_positions: int = Field(gt=0)
    sleeve_allocation_pct: Decimal = Field(gt=0)
    max_daily_loss_pct: Decimal = Field(gt=0)
    liquidity_cap_pct_of_adv: Decimal = Field(gt=0)
    concentration_limit_pct: Decimal = Field(gt=0)
    max_risk_distance_pct_of_entry: Decimal = Field(gt=0, default=Decimal("20"))
    lot_size: Decimal = Field(gt=0, default=Decimal(1))


class RiskConfig(BaseModel):
    """`risk.yaml` resolved for one check() call: global + the signal's sleeve."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    stale_data_seconds: int = Field(gt=0)
    order_price_band_pct: Decimal = Field(gt=0)
    max_open_positions_total: int = Field(gt=0)
    max_portfolio_drawdown_pct: Decimal = Field(gt=0)
    auto_paper_shadow: bool = False
    sleeve: SleeveConfig


class InstanceState(BaseModel):
    """One strategy instance's pause/concurrency state."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    paused: bool = False
    open_symbols: tuple[str, ...] = ()


class SleeveState(BaseModel):
    """Runtime numbers the risk engine needs for one sleeve, right now."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    equity: Decimal = Field(gt=0)
    open_position_value: Decimal = Field(ge=0)
    open_position_count: int = Field(ge=0)
    daily_pnl_pct: Decimal
    symbol_risk_pct: dict[str, Decimal] = Field(default_factory=dict)


class PortfolioState(BaseModel):
    """Everything `RiskEngine.check()` needs beyond the signal itself."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sleeve: SleeveState
    instance: InstanceState
    total_open_positions: int = Field(ge=0)
    portfolio_drawdown_pct: Decimal = Field(ge=0)
    last_tick_price: Decimal | None = Field(default=None, gt=0)
    liquidity_cap_qty: Decimal = Field(gt=0)
    decided_signal_ids: frozenset[str] = Field(default_factory=frozenset)
    extra: dict[str, Any] = Field(default_factory=dict)
