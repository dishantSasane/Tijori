"""Ranking metrics for completed backtest trades (docs/BUILD_ORDER.md P1c).

`scorecard.py` already covers win/loss/profit-factor/expectancy/drawdown.
This module adds the rest of the ranking-metric set BUILD_ORDER.md §P1c
requires before any candidate is compared: Calmar/Sharpe/Sortino, turnover
and cost sensitivity, % profitable instruments, % profitable time windows,
a block-bootstrap confidence interval on mean return (reusing
`bootstrap.moving_block_mean_interval`, not a second implementation), and
performance vs. buy-and-hold. Raw rupee P&L is never a ranking key -- every
ratio here is computed on returns, not currency amounts.

`Trade` (runner.py) carries neither symbol nor a calendar timestamp, and
runner.py is active work elsewhere -- this module takes that metadata as
caller-supplied, keyed by `signal_id`, instead of extending `Trade`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, localcontext

from trading.backtest.bootstrap import BootstrapInterval, moving_block_mean_interval
from trading.backtest.multiple_testing import mean
from trading.backtest.runner import Trade


def trade_returns(trades: Sequence[Trade], *, starting_equity: Decimal) -> list[Decimal]:
    """Per-trade return on `starting_equity`, in the runner's own emission order."""
    if starting_equity <= 0:
        raise ValueError("starting_equity must be positive")
    return [trade.pnl / starting_equity for trade in trades]


def _sample_stdev(values: Sequence[Decimal]) -> Decimal:
    if len(values) < 2:
        return Decimal(0)
    avg = mean(list(values))
    variance = sum((value - avg) ** 2 for value in values) / Decimal(len(values) - 1)
    with localcontext() as context:
        context.prec = 40
        return variance.sqrt()


def _decimal_sqrt(value: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = 40
        return value.sqrt()


def sharpe_ratio(returns: Sequence[Decimal], *, periods_per_year: int) -> Decimal:
    """Mean / stdev of per-period returns, annualized. 0 if too few periods or
    zero variance (never a divide-by-zero crash -- an edge case `nan`/`inf`
    would silently corrupt a ranking table)."""
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    if len(returns) < 2:
        return Decimal(0)
    spread = _sample_stdev(returns)
    if spread == 0:
        return Decimal(0)
    return mean(list(returns)) / spread * _decimal_sqrt(Decimal(periods_per_year))


def sortino_ratio(returns: Sequence[Decimal], *, periods_per_year: int) -> Decimal:
    """Like `sharpe_ratio` but penalizes only downside deviation below zero."""
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    if not returns:
        return Decimal(0)
    downside_sq = sum(min(value, Decimal(0)) ** 2 for value in returns) / Decimal(len(returns))
    downside = _decimal_sqrt(downside_sq)
    if downside == 0:
        return Decimal(0)
    return mean(list(returns)) / downside * _decimal_sqrt(Decimal(periods_per_year))


def calmar_ratio(*, annualized_return_pct: Decimal, max_drawdown_pct: Decimal) -> Decimal:
    """Annualized return / max drawdown, both expressed as percentages of
    starting equity. 0 if there was no drawdown to divide by."""
    if max_drawdown_pct <= 0:
        return Decimal(0)
    return annualized_return_pct / max_drawdown_pct


def annualized_return_pct(*, total_return_pct: Decimal, years: Decimal) -> Decimal:
    if years <= 0:
        raise ValueError("years must be positive")
    growth = Decimal(1) + total_return_pct / Decimal(100)
    if growth <= 0:
        # a >=100% loss has no real annualized rate; report the floor.
        return Decimal(-100)
    with localcontext() as context:
        context.prec = 40
        annualized_growth = growth ** (Decimal(1) / years)
    return (annualized_growth - Decimal(1)) * Decimal(100)


@dataclass(frozen=True)
class TurnoverAndCosts:
    turnover_ratio: Decimal
    """Total traded notional / starting equity -- how many times over the
    starting capital was put to work, not a bounded percentage."""
    cost_pct_of_notional: Decimal
    """Total fees / total notional traded -- cost sensitivity, independent of
    how much capital was deployed."""


def turnover_and_cost_sensitivity(
    trades: Sequence[Trade], *, starting_equity: Decimal
) -> TurnoverAndCosts:
    if starting_equity <= 0:
        raise ValueError("starting_equity must be positive")
    if not trades:
        return TurnoverAndCosts(Decimal(0), Decimal(0))
    total_notional = sum((trade.quantity * trade.entry_price for trade in trades), Decimal(0))
    total_fees = sum((trade.fees for trade in trades), Decimal(0))
    return TurnoverAndCosts(
        turnover_ratio=total_notional / starting_equity,
        cost_pct_of_notional=(total_fees / total_notional if total_notional else Decimal(0)),
    )


def _pct_profitable_groups(
    trades: Sequence[Trade], group_by_signal_id: Mapping[str, str]
) -> Decimal:
    pnl_by_group: dict[str, Decimal] = {}
    for trade in trades:
        group = group_by_signal_id.get(trade.signal_id)
        if group is None:
            raise KeyError(f"no group label supplied for signal_id={trade.signal_id!r}")
        pnl_by_group[group] = pnl_by_group.get(group, Decimal(0)) + trade.pnl
    if not pnl_by_group:
        return Decimal(0)
    profitable = sum(1 for total in pnl_by_group.values() if total > 0)
    return Decimal(profitable) / Decimal(len(pnl_by_group)) * Decimal(100)


def pct_profitable_instruments(
    trades: Sequence[Trade], *, symbol_by_signal_id: Mapping[str, str]
) -> Decimal:
    """% of distinct instruments (grouped by caller-supplied symbol) with net
    positive P&L -- a strategy profitable only on one name is weaker than one
    that works broadly, even at equal total P&L."""
    return _pct_profitable_groups(trades, symbol_by_signal_id)


def pct_profitable_time_windows(
    trades: Sequence[Trade], *, window_by_signal_id: Mapping[str, str]
) -> Decimal:
    """% of time buckets (caller-supplied label, e.g. year-month) with net
    positive P&L -- flags an edge that only existed in one regime/period."""
    return _pct_profitable_groups(trades, window_by_signal_id)


def vs_buy_and_hold_pct(
    *, strategy_total_return_pct: Decimal, buy_and_hold_return_pct: Decimal
) -> Decimal:
    """Excess return over simply holding the instrument -- a positive-P&L
    strategy that trails buy-and-hold is not actually adding value."""
    return strategy_total_return_pct - buy_and_hold_return_pct


def bootstrap_mean_return_interval(
    returns: Sequence[Decimal], *, block_size: int = 20, replicates: int = 10_000, seed: int
) -> BootstrapInterval:
    """Moving-block bootstrap CI on mean per-period return -- the ranking
    metric BUILD_ORDER.md calls for; delegates entirely to the existing
    `bootstrap.moving_block_mean_interval` rather than a second implementation.
    """
    return moving_block_mean_interval(
        list(returns), block_size=block_size, replicates=replicates, seed=seed
    )
