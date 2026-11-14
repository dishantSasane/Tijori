"""Small, deterministic scorecard calculations for completed backtest trades."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from trading.backtest.runner import Trade


@dataclass(frozen=True)
class Scorecard:
    trades: int
    wins: int
    losses: int
    win_rate: Decimal
    total_pnl: Decimal
    max_drawdown: Decimal
    profit_factor: Decimal


def scorecard(trades: list[Trade]) -> Scorecard:
    """Summarize completed trades; unfilled/open trades are excluded upstream."""
    if not trades:
        return Scorecard(0, 0, 0, Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"))
    wins = sum(trade.pnl > 0 for trade in trades)
    losses = sum(trade.pnl < 0 for trade in trades)
    total = sum((trade.pnl for trade in trades), Decimal("0"))
    gross_profit = sum((trade.pnl for trade in trades if trade.pnl > 0), Decimal("0"))
    gross_loss = -sum((trade.pnl for trade in trades if trade.pnl < 0), Decimal("0"))
    peak = Decimal("0")
    equity = Decimal("0")
    max_drawdown = Decimal("0")
    for trade in trades:
        equity += trade.pnl
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    profit_factor = gross_profit / gross_loss if gross_loss else Decimal("0")
    return Scorecard(
        trades=len(trades),
        wins=wins,
        losses=losses,
        win_rate=Decimal(wins) / Decimal(len(trades)),
        total_pnl=total,
        max_drawdown=max_drawdown,
        profit_factor=profit_factor,
    )
