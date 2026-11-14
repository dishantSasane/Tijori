"""Machine-readable Phase-1 scorecard reports."""

from __future__ import annotations

import json
from datetime import UTC
from decimal import Decimal
from pathlib import Path
from typing import Any

from trading.backtest.fills import BacktestProfile
from trading.backtest.phase1 import StrategyBacktest, run_t1, run_t4
from trading.backtest.walk_forward import rolling_walk_forward_windows
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


def write_phase1_walk_forward_report(
    candles: list[Candle],
    *,
    output: Path,
    quantity: Decimal,
    profile: BacktestProfile,
    universe_id: str,
    data_status: str,
    train_bars: int,
    test_bars: int,
    step_bars: int | None = None,
    embargo_bars: int = 1,
) -> Path:
    """Write chronological T1/T4 window results with no cross-window leakage."""
    if not candles:
        raise ValueError("cannot report on an empty candle series")
    windows = rolling_walk_forward_windows(
        candles,
        train_bars=train_bars,
        test_bars=test_bars,
        step_bars=step_bars,
        embargo_bars=embargo_bars,
    )
    strategy_windows: dict[str, list[dict[str, Any]]] = {
        "t1_donchian": [],
        "t4_rsi_pullback": [],
    }
    for window in windows:
        window_candles = candles[: window.test_end]
        signal_start = candles[window.test_start].ts_open_utc
        signal_end = (
            candles[window.test_end].ts_open_utc if window.test_end < len(candles) else None
        )
        results = (
            run_t1(
                window_candles,
                quantity=quantity,
                profile=profile,
                signal_start=signal_start,
                signal_end=signal_end,
            ),
            run_t4(
                window_candles,
                quantity=quantity,
                profile=profile,
                signal_start=signal_start,
                signal_end=signal_end,
            ),
        )
        for result in results:
            strategy_windows[result.strategy_id].append(
                {
                    "train": {
                        "start": candles[window.train_start]
                        .ts_open_utc.astimezone(UTC)
                        .isoformat(),
                        "end": candles[window.train_end - 1]
                        .ts_open_utc.astimezone(UTC)
                        .isoformat(),
                        "bars": window.train_end - window.train_start,
                    },
                    "test": {
                        "start": signal_start.astimezone(UTC).isoformat(),
                        "end": candles[window.test_end - 1].ts_open_utc.astimezone(UTC).isoformat(),
                        "bars": window.test_end - window.test_start,
                    },
                    **_strategy_report(result),
                }
            )
    report = {
        "report_type": "p1_strategy_walk_forward_scorecard",
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
        "validation": {
            "label": "retrospective_walk_forward",
            "boundary_policy": "censor_open_positions_at_test_end",
            "train_bars": train_bars,
            "test_bars": test_bars,
            "step_bars": test_bars if step_bars is None else step_bars,
            "embargo_bars": embargo_bars,
            "window_count": len(windows),
        },
        "strategies": strategy_windows,
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
