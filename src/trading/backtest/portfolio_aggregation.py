"""Portfolio aggregation contract (docs/specs/P1_EVALUATION.md: "Future
portfolio aggregation must state how simultaneous signals, 1% risk sizing,
cash reservations, capital limits, and conflicts are handled").

This answers the one-line forward reference with a real, tested module, not
another spec sentence. It generalizes `P1_REJECTION_RULE.md`'s already-made
decision for the five-symbol pilot -- "compute each symbol's return on its
own fixed research capital after costs, then take the arithmetic mean across
the five symbols" -- from exactly five instruments to any N.

**Default weighting: equal-weight.** Not a new choice invented here; it is
the five-symbol pilot's own already-chosen convention, generalized. Equal-
weight matches the existing P1b/c sizing discipline (ADR-0026: every
candidate is sized identically -- 1% risk per trade on the same placeholder
research capital), so no instrument's return is more "real money" than
another's. Flagged explicitly as a methodology choice, not a silent
assumption: turnover-weighting or capital-weighting were considered and
NOT chosen. Either could be named as an alternative in a future ADR if the
owner wants it; this module does not hard-code equal-weight as the only
possible answer, callers may supply their own weights via
`weighted_panel_returns`.

**Simultaneous signals, cash reservations, capital limits, conflicts.**
This module only ever sees already-resolved per-instrument daily return
series -- it never sees raw signals or trades. Conflict resolution already
happens inside `runner.run_long_only` (single-position-at-a-time per
instrument, `rejected:concurrent_position_exists` audit events) before a
return series ever reaches this module. There is **no shared capital pool**
here: exactly as `P1_REJECTION_RULE.md` already states for the five-symbol
panel, "this panel statistic estimates average per-instrument edge; it is
not a funded portfolio return and must not be used to claim pooled P&L,
portfolio Sharpe, portfolio drawdown, or deployable capital performance."
A true funded, capital-constrained multi-instrument replay (one shared cash
pool, margin, simultaneous-signal capital competition) is a materially
different, larger engine that does not exist anywhere in this codebase yet
(every existing runner is single-instrument, fixed-capital) -- building one
is explicitly OUT OF SCOPE here and remains a separate future decision, not
something this module should quietly pretend to solve.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal


def equal_weight_panel_returns(
    returns_by_instrument: Mapping[str, Sequence[Decimal]],
) -> list[Decimal]:
    """Equal-weight mean of per-instrument daily returns, date-index aligned.

    Every instrument's series must already be aligned to the same ordered
    session calendar and have the same length -- this function does not
    align calendars itself (same "caller is responsible for completeness"
    discipline as `research_universe.build_snapshot`). A missing day for one
    instrument is never silently dropped or treated as zero; the caller must
    resolve coverage before calling this (same as the existing P1a action-
    preflight/coverage gates).
    """
    return weighted_panel_returns(
        returns_by_instrument,
        weights={instrument: Decimal(1) for instrument in returns_by_instrument},
    )


def weighted_panel_returns(
    returns_by_instrument: Mapping[str, Sequence[Decimal]],
    *,
    weights: Mapping[str, Decimal],
) -> list[Decimal]:
    """Weighted mean of per-instrument daily returns. `weights` need not sum
    to 1 -- they are normalized here, so callers can pass raw turnover or
    capital figures directly. Fails closed on misaligned series, an empty
    panel, a non-positive weight, or a weight supplied for an instrument not
    in `returns_by_instrument` (or vice versa) -- never silently drops or
    pads a series.
    """
    if not returns_by_instrument:
        raise ValueError("at least one instrument is required")
    if set(returns_by_instrument) != set(weights):
        raise ValueError("weights must cover exactly the supplied instruments")
    lengths = {len(series) for series in returns_by_instrument.values()}
    if len(lengths) != 1:
        raise ValueError("every instrument's return series must be the same aligned length")
    (length,) = lengths
    if length == 0:
        raise ValueError("return series must not be empty")
    if any(not weight.is_finite() for weight in weights.values()):
        raise ValueError("weights must be finite (no NaN/Infinity)")
    if any(weight <= 0 for weight in weights.values()):
        raise ValueError("weights must be strictly positive")
    if any(not value.is_finite() for series in returns_by_instrument.values() for value in series):
        raise ValueError("returns must be finite (no NaN/Infinity)")
    total_weight = sum(weights.values(), Decimal(0))
    normalized = {instrument: weight / total_weight for instrument, weight in weights.items()}

    panel: list[Decimal] = []
    for day_index in range(length):
        panel.append(
            sum(
                (
                    returns_by_instrument[instrument][day_index] * normalized[instrument]
                    for instrument in returns_by_instrument
                ),
                Decimal(0),
            )
        )
    return panel


def daily_excess_returns(
    panel_returns: Sequence[Decimal], cash_daily_returns: Sequence[Decimal] | Decimal
) -> list[Decimal]:
    """Panel return minus cash, per day -- `P1_REJECTION_RULE.md`'s "raw test
    is mean daily excess return versus cash". `cash_daily_returns` may be one
    constant (a flat assumed cash rate) or a per-day series of the same
    length as `panel_returns`.
    """
    if not panel_returns:
        raise ValueError("panel_returns must not be empty")
    if isinstance(cash_daily_returns, Decimal):
        return [value - cash_daily_returns for value in panel_returns]
    if len(cash_daily_returns) != len(panel_returns):
        raise ValueError("cash_daily_returns must match panel_returns length when a series")
    return [
        panel_value - cash_value
        for panel_value, cash_value in zip(panel_returns, cash_daily_returns, strict=True)
    ]


def portfolio_equity_curve(
    daily_returns: Sequence[Decimal], *, starting_equity: Decimal
) -> list[Decimal]:
    """Compounding equity curve from a daily return series -- the one
    primitive both `calmar_ratio`'s drawdown input and the panel's total
    return need, that `metrics.py` never had to build itself (its callers
    passed an already-known total-return/drawdown pair).
    """
    if starting_equity <= 0:
        raise ValueError("starting_equity must be positive")
    equity = starting_equity
    curve = [equity]
    for daily_return in daily_returns:
        equity *= Decimal(1) + daily_return
        curve.append(equity)
    return curve


def max_drawdown_pct_from_curve(curve: Sequence[Decimal]) -> Decimal:
    """Max peak-to-trough drawdown as a percentage of the peak, from an
    equity curve (e.g. `portfolio_equity_curve`'s output).
    """
    if len(curve) < 2:
        raise ValueError("curve must have at least two points")
    peak = curve[0]
    worst = Decimal(0)
    for value in curve[1:]:
        peak = max(peak, value)
        if peak > 0:
            worst = max(worst, (peak - value) / peak * Decimal(100))
    return worst


def profitable_instrument_counts(
    cumulative_return_by_instrument: Mapping[str, Decimal],
) -> tuple[int, int]:
    """(profitable_count, instrument_count) for `promotion.HoldoutEvidence`'s
    `profitable_instruments`/`instrument_count` fields -- and the natural
    input to a binomial test on the profitable-instrument fraction, at any N,
    rather than a fixed "X of 5" that only made sense for the pilot's exact
    size. "Profitable" means strictly positive cumulative return, same
    definition `P1_REJECTION_RULE.md` already uses ("zero counts as not
    profitable").
    """
    if not cumulative_return_by_instrument:
        raise ValueError("at least one instrument is required")
    profitable = sum(1 for value in cumulative_return_by_instrument.values() if value > 0)
    return profitable, len(cumulative_return_by_instrument)


@dataclass(frozen=True)
class PortfolioAggregation:
    """Everything `ranking_report.build_ranking_report_row` and
    `promotion.HoldoutEvidence` need from a multi-instrument panel, computed
    once from the same aligned per-instrument inputs.
    """

    panel_returns: tuple[Decimal, ...]
    excess_returns: tuple[Decimal, ...]
    equity_curve: tuple[Decimal, ...]
    max_drawdown_pct: Decimal
    profitable_instruments: int
    instrument_count: int


def aggregate_portfolio(
    returns_by_instrument: Mapping[str, Sequence[Decimal]],
    *,
    cumulative_return_by_instrument: Mapping[str, Decimal],
    cash_daily_returns: Sequence[Decimal] | Decimal,
    starting_equity: Decimal,
    weights: Mapping[str, Decimal] | None = None,
) -> PortfolioAggregation:
    """One call producing the complete panel the ranking report and holdout
    evidence both need. `cumulative_return_by_instrument` is caller-supplied
    rather than derived from `returns_by_instrument` here, since "cumulative"
    can legitimately mean different things (compounded vs. simple, full
    window vs. holdout-only) -- this function does not guess which the
    caller means.

    `returns_by_instrument` and `cumulative_return_by_instrument` must name
    the exact same instrument set. Without this check, panel returns could
    be computed for A/B while the profitable-instrument count (which feeds
    the binomial promotion gate directly) silently reported on an unrelated
    C, or omitted A/B entirely -- corrupting the gate rather than erroring.
    """
    if set(returns_by_instrument) != set(cumulative_return_by_instrument):
        raise ValueError(
            "returns_by_instrument and cumulative_return_by_instrument must "
            "name the exact same instrument set"
        )
    if any(not value.is_finite() for value in cumulative_return_by_instrument.values()):
        raise ValueError("cumulative returns must be finite (no NaN/Infinity)")
    if isinstance(cash_daily_returns, Decimal):
        if not cash_daily_returns.is_finite():
            raise ValueError("cash_daily_returns must be finite (no NaN/Infinity)")
    elif any(not value.is_finite() for value in cash_daily_returns):
        raise ValueError("cash_daily_returns must be finite (no NaN/Infinity)")

    panel = (
        weighted_panel_returns(returns_by_instrument, weights=weights)
        if weights is not None
        else equal_weight_panel_returns(returns_by_instrument)
    )
    excess = daily_excess_returns(panel, cash_daily_returns)
    curve = portfolio_equity_curve(panel, starting_equity=starting_equity)
    drawdown = max_drawdown_pct_from_curve(curve)
    profitable, total = profitable_instrument_counts(cumulative_return_by_instrument)
    return PortfolioAggregation(
        panel_returns=tuple(panel),
        excess_returns=tuple(excess),
        equity_curve=tuple(curve),
        max_drawdown_pct=drawdown,
        profitable_instruments=profitable,
        instrument_count=total,
    )
