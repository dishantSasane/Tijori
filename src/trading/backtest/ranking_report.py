"""Assembles one P1c ranking-report row per candidate (docs/BUILD_ORDER.md's
P1c exit criteria: "the ranking report states which correction method was
applied and shows results both with and without it").

This combines `scorecard.py`, `metrics.py`, `bootstrap.py` and
`multiple_testing.py` -- all already built -- into the one thing that was
still missing. It deliberately does NOT solve the still-open portfolio
aggregation / daily-return-construction question (BUILD_ORDER.md: "no
ranking report can be produced until P1a's source/split gates and the
portfolio aggregation contract are settled"): `daily_excess_returns` is a
caller-supplied input here, exactly like `metrics.py`'s symbol/window
grouping maps are caller-supplied. The moment a real daily series exists,
this assembles the report; it does not pretend to build that series itself.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from trading.backtest.bootstrap import BootstrapInterval
from trading.backtest.metrics import (
    TurnoverAndCosts,
    annualized_return_pct,
    bootstrap_mean_return_interval,
    calmar_ratio,
    pct_profitable_instruments,
    pct_profitable_time_windows,
    sharpe_ratio,
    sortino_ratio,
    trade_returns,
    turnover_and_cost_sensitivity,
    vs_buy_and_hold_pct,
)
from trading.backtest.multiple_testing import (
    P1_FAMILY_SIZE,
    bonferroni_adjust,
    moving_block_excess_p_value,
)
from trading.backtest.runner import Trade
from trading.backtest.scorecard import Scorecard, scorecard


@dataclass(frozen=True)
class RankingReportRow:
    candidate_id: str
    timeframe: str
    """Caller-supplied grouping label (e.g. "daily"/"intraday") for display
    only -- every row uses the same `family_size` regardless of this label.
    """
    dataset_manifest_hash: str
    """Identity of the exact frozen data snapshot (candles + corporate-action
    coverage + calendar version) this row was computed against -- opaque to
    this module; Codex's P1a snapshot-manifest contract defines what goes
    into it. A report row with no hash, or two rows claiming the same
    candidate under different hashes, is not a comparable result.
    """
    scorecard: Scorecard
    max_drawdown_pct: Decimal
    sharpe: Decimal
    sortino: Decimal
    calmar: Decimal
    turnover: TurnoverAndCosts
    raw_p_value: Decimal
    adjusted_p_value: Decimal
    family_size: int
    bootstrap_interval: BootstrapInterval
    pct_profitable_instruments: Decimal | None = None
    pct_profitable_time_windows: Decimal | None = None
    vs_buy_and_hold_pct: Decimal | None = None


def build_ranking_report_row(
    *,
    candidate_id: str,
    timeframe: str,
    dataset_manifest_hash: str,
    trades: Sequence[Trade],
    starting_equity: Decimal,
    daily_excess_returns: Sequence[Decimal],
    periods_per_year: int,
    years: Decimal,
    bootstrap_seed: int,
    family_size: int = P1_FAMILY_SIZE,
    bootstrap_block_size: int = 20,
    bootstrap_replicates: int = 10_000,
    symbol_by_signal_id: Mapping[str, str] | None = None,
    window_by_signal_id: Mapping[str, str] | None = None,
    buy_and_hold_return_pct: Decimal | None = None,
) -> RankingReportRow:
    """One row, raw and Bonferroni-adjusted side by side -- never only the
    adjusted figure, so a reader can see what the correction actually did.
    """
    if starting_equity <= 0:
        raise ValueError("starting_equity must be positive")
    if not dataset_manifest_hash:
        raise ValueError(
            "dataset_manifest_hash is required -- a row not tied to a frozen "
            "data snapshot is not a comparable result"
        )
    card = scorecard(list(trades))
    max_drawdown_pct = card.max_drawdown / starting_equity * Decimal(100)
    returns = trade_returns(trades, starting_equity=starting_equity)
    total_return_pct = card.total_pnl / starting_equity * Decimal(100)

    raw_p = moving_block_excess_p_value(
        list(daily_excess_returns),
        block_size=bootstrap_block_size,
        replicates=bootstrap_replicates,
        seed=bootstrap_seed,
    )
    adjusted_p = bonferroni_adjust(raw_p, family_size)
    interval = bootstrap_mean_return_interval(
        daily_excess_returns,
        block_size=bootstrap_block_size,
        replicates=bootstrap_replicates,
        seed=bootstrap_seed,
    )

    return RankingReportRow(
        candidate_id=candidate_id,
        timeframe=timeframe,
        dataset_manifest_hash=dataset_manifest_hash,
        scorecard=card,
        max_drawdown_pct=max_drawdown_pct,
        sharpe=sharpe_ratio(returns, periods_per_year=periods_per_year),
        sortino=sortino_ratio(returns, periods_per_year=periods_per_year),
        calmar=calmar_ratio(
            annualized_return_pct=annualized_return_pct(
                total_return_pct=total_return_pct, years=years
            ),
            max_drawdown_pct=max_drawdown_pct,
        ),
        turnover=turnover_and_cost_sensitivity(trades, starting_equity=starting_equity),
        raw_p_value=raw_p,
        adjusted_p_value=adjusted_p,
        family_size=family_size,
        bootstrap_interval=interval,
        pct_profitable_instruments=(
            pct_profitable_instruments(trades, symbol_by_signal_id=symbol_by_signal_id)
            if symbol_by_signal_id is not None
            else None
        ),
        pct_profitable_time_windows=(
            pct_profitable_time_windows(trades, window_by_signal_id=window_by_signal_id)
            if window_by_signal_id is not None
            else None
        ),
        vs_buy_and_hold_pct=(
            vs_buy_and_hold_pct(
                strategy_total_return_pct=total_return_pct,
                buy_and_hold_return_pct=buy_and_hold_return_pct,
            )
            if buy_and_hold_return_pct is not None
            else None
        ),
    )
