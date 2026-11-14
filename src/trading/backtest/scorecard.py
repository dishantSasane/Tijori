"""Small, deterministic scorecard calculations for completed backtest trades."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import ceil
from random import Random

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


@dataclass(frozen=True)
class ExpectancyInterval:
    """A deterministic confidence interval for mean trade P&L."""

    lower: Decimal
    upper: Decimal
    confidence: Decimal
    block_size: int
    resamples: int
    seed: int


def scorecard(trades: list[Trade]) -> Scorecard:
    """Summarize completed trades; unfilled/open trades are excluded upstream."""
    if not trades:
        zero = Decimal("0")
        return Scorecard(0, 0, 0, zero, zero, zero, zero, zero, zero, zero)
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
    )


def block_bootstrap_expectancy(
    trades: list[Trade],
    *,
    block_size: int = 5,
    resamples: int = 2_000,
    confidence: Decimal = Decimal("0.95"),
    seed: int = 20261115,
) -> ExpectancyInterval:
    """Estimate an expectancy interval while preserving local trade blocks.

    This circular block bootstrap is a deterministic uncertainty estimate for
    one chronological instrument series. It is not a proof of independence,
    and it must not be used to tune strategy parameters.
    """
    if block_size <= 0 or resamples <= 0:
        raise ValueError("block_size and resamples must be positive")
    if not Decimal("0") < confidence < Decimal("1"):
        raise ValueError("confidence must be between zero and one")
    if not trades:
        zero = Decimal("0")
        return ExpectancyInterval(zero, zero, confidence, block_size, resamples, seed)
    pnls = [trade.pnl for trade in trades]
    block_count = ceil(len(pnls) / block_size)
    rng = Random(seed)
    means: list[Decimal] = []
    for _ in range(resamples):
        sample: list[Decimal] = []
        for _ in range(block_count):
            start = rng.randrange(len(pnls))
            sample.extend(pnls[(start + offset) % len(pnls)] for offset in range(block_size))
        means.append(sum(sample[: len(pnls)], Decimal("0")) / Decimal(len(pnls)))
    means.sort()
    tail = (Decimal("1") - confidence) / Decimal("2")
    lower_index = max(0, min(len(means) - 1, int(tail * Decimal(resamples))))
    upper_index = max(
        0,
        min(len(means) - 1, int((Decimal("1") - tail) * Decimal(resamples)) - 1),
    )
    return ExpectancyInterval(
        lower=means[lower_index],
        upper=means[upper_index],
        confidence=confidence,
        block_size=block_size,
        resamples=resamples,
        seed=seed,
    )
