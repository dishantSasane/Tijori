"""Machine-readable Phase-1 scorecard reports."""

from __future__ import annotations

import json
from datetime import UTC
from decimal import Decimal
from pathlib import Path
from typing import Any

from trading.backtest.fills import BacktestProfile
from trading.backtest.phase1 import StrategyBacktest, run_t1, run_t4
from trading.core.models import Candle


def write_phase1_report(
    candles: list[Candle],
    *,
    output: Path,
    quantity: Decimal,
    profile: BacktestProfile,
    universe_id: str,
    data_status: str,
) -> Path:
    """Run T1/T4 and write a reproducible research-only JSON report."""
    if not candles:
        raise ValueError("cannot report on an empty candle series")
    results = {
        "t1_donchian": run_t1(candles, quantity=quantity, profile=profile),
        "t4_rsi_pullback": run_t4(candles, quantity=quantity, profile=profile),
    }
    report = {
        "report_type": "p1_strategy_scorecard",
        "status": "research_only",
        "universe_id": universe_id,
        "data_status": data_status,
        "market": candles[0].market.value,
        "symbol": candles[0].symbol,
        "timeframe": candles[0].timeframe.value,
        "coverage": {
            "bars": len(candles),
            "start": candles[0].ts_open_utc.astimezone(UTC).isoformat(),
            "end": candles[-1].ts_open_utc.astimezone(UTC).isoformat(),
        },
        "strategies": {name: _strategy_report(result) for name, result in results.items()},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def _strategy_report(result: StrategyBacktest) -> dict[str, Any]:
    score = result.result.scorecard
    return {
        "signals": len(result.signals),
        "trades": score.trades,
        "scorecard": {
            "wins": score.wins,
            "losses": score.losses,
            "win_rate": str(score.win_rate),
            "total_pnl": str(score.total_pnl),
            "max_drawdown": str(score.max_drawdown),
            "profit_factor": str(score.profit_factor),
            "avg_win": str(score.avg_win),
            "avg_loss": str(score.avg_loss),
            "expectancy": str(score.expectancy),
        },
        "equivalence_checked": result.result.primary == result.result.reference,
        "open_positions": result.result.primary.open_positions,
        "unfilled_signals": len(result.result.primary.unfilled_signals),
    }
