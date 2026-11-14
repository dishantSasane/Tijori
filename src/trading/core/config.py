"""Config loading. Real config lives in `config/*.yaml` (git-ignored); templates
ending `.example.yaml` are committed (AGENTS.md §6).

Only the `global` risk block is modeled strictly here, since the risk engine
depends on it directly. Sleeve/market profiles are intentionally loaded as
plain dicts for now — docs/specs/RISK_ENGINE_SPEC.md and the per-sleeve/market
models land with the risk engine implementation, not before it exists.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

from trading.core.enums import Mode


class RiskGlobalConfig(BaseModel):
    """`risk.yaml` -> `global` block. See docs/RISK_SPEC.md."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: Mode
    paper_capital_inr: Decimal
    max_portfolio_drawdown_pct: Decimal
    max_daily_loss_pct: Decimal
    max_open_positions_total: int
    stale_data_seconds: int
    order_price_band_pct: Decimal


class ConfigNotFoundError(FileNotFoundError):
    """Raised when neither the real nor the example config file exists."""


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file into a dict. Falls back to `<path>.example.<ext>` so the
    repo works out of the box before the owner copies and edits real config,
    but never silently falls back if neither file exists.
    """
    if not path.exists():
        example = path.with_name(path.stem + ".example" + path.suffix)
        if not example.exists():
            raise ConfigNotFoundError(f"neither {path} nor {example} exists")
        path = example
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def load_risk_global_config(config_dir: Path) -> RiskGlobalConfig:
    data = load_yaml(config_dir / "risk.yaml")
    return RiskGlobalConfig.model_validate(data["global"])
