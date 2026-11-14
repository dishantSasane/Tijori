"""Deterministic validation of the primary and reference backtesters."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from trading.backtest.fills import BacktestProfile
from trading.backtest.reference import run_reference
from trading.backtest.runner import BacktestResult, run_long_only
from trading.backtest.scorecard import Scorecard, scorecard
from trading.core.models import Candle, Signal


class BacktestMismatchError(AssertionError):
    """Raised when the primary and independent reference runners disagree."""


@dataclass(frozen=True)
class ValidatedBacktest:
    """Both runner results and the scorecard derived from completed trades."""

    primary: BacktestResult
    reference: BacktestResult
    scorecard: Scorecard


def validate_long_only(
    candles: list[Candle],
    signals: list[Signal],
    *,
    quantity: Decimal,
    profile: BacktestProfile,
    condition_exit: Callable[[Signal, int, Candle], bool] | None = None,
) -> ValidatedBacktest:
    """Run both implementations and refuse to score divergent results."""
    primary = run_long_only(
        candles,
        signals,
        quantity=quantity,
        profile=profile,
        condition_exit=condition_exit,
    )
    reference = run_reference(
        candles,
        signals,
        quantity=quantity,
        profile=profile,
        condition_exit=condition_exit,
    )
    if primary != reference:
        raise BacktestMismatchError("primary and reference backtesters disagree")
    return ValidatedBacktest(
        primary=primary,
        reference=reference,
        scorecard=scorecard(primary.trades),
    )
