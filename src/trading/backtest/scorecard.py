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
    avg_win: Decimal
    avg_loss: Decimal
    expectancy: Decimal
    activation_opportunities: int | None = None
    activation_eligible: int | None = None
    activation_frequency: Decimal | None = None


def scorecard(
    trades: list[Trade],
    *,
    activation_opportunities: int | None = None,
    activation_eligible: int | None = None,
) -> Scorecard:
    """Summarize completed trades; unfilled/open trades are excluded upstream."""
    activation_frequency: Decimal | None = None
    if activation_opportunities is None or activation_eligible is None:
        if activation_opportunities is not None or activation_eligible is not None:
            raise ValueError(
                "activation opportunities and eligible counts must be supplied together"
            )
    else:
        if (
            isinstance(activation_opportunities, bool)
            or not isinstance(activation_opportunities, int)
            or isinstance(activation_eligible, bool)
            or not isinstance(activation_eligible, int)
            or activation_opportunities < 0
            or not 0 <= activation_eligible <= activation_opportunities
        ):
            raise ValueError(
                "activation counts must be integers with 0 <= eligible <= opportunities"
            )
        if activation_opportunities:
            activation_frequency = Decimal(activation_eligible) / Decimal(activation_opportunities)
    if not trades:
        zero = Decimal("0")
        return Scorecard(
            0,
            0,
            0,
            zero,
            zero,
            zero,
            zero,
            zero,
            zero,
            zero,
            activation_opportunities,
            activation_eligible,
            activation_frequency,
        )
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
    avg_win = gross_profit / Decimal(wins) if wins else Decimal("0")
    avg_loss = -gross_loss / Decimal(losses) if losses else Decimal("0")
    return Scorecard(
        trades=len(trades),
        wins=wins,
        losses=losses,
        win_rate=Decimal(wins) / Decimal(len(trades)),
        total_pnl=total,
        max_drawdown=max_drawdown,
        profit_factor=profit_factor,
        avg_win=avg_win,
        avg_loss=avg_loss,
        expectancy=total / Decimal(len(trades)),
        activation_opportunities=activation_opportunities,
        activation_eligible=activation_eligible,
        activation_frequency=activation_frequency,
    )
