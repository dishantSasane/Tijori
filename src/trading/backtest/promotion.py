"""Pre-registered, one-shot holdout decision rules for P1 candidates."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from trading.core.enums import Timeframe

HoldoutStatus = Literal["pass_to_paper", "rejected", "inconclusive"]
P1_HOLDOUT_FAMILY_SIZE = 15
P1_PILOT_INSTRUMENT_COUNT = 5
P1_HOLDOUT_BLOCK_COUNT = 3
P1_FAMILY_ALPHA = Decimal("0.05")


@dataclass(frozen=True)
class HoldoutEvidence:
    """Frozen candidate-level statistics prepared before the holdout decision."""

    timeframe: Timeframe
    completed_trades: int
    family_size: int
    mean_daily_excess_return_after_costs: Decimal | None
    bonferroni_adjusted_p_value: Decimal | None
    bootstrap_ci_lower_bound: Decimal | None
    profitable_instruments: int
    instrument_count: int
    profitable_time_blocks: int
    time_block_count: int
    data_complete: bool


@dataclass(frozen=True)
class HoldoutDecision:
    status: HoldoutStatus
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status not in {"pass_to_paper", "rejected", "inconclusive"}:
            raise ValueError("holdout decision has an unknown status")
        if (
            not isinstance(self.reasons, tuple)
            or not self.reasons
            or any(not isinstance(reason, str) or not reason for reason in self.reasons)
        ):
            raise ValueError("holdout decision requires non-empty tuple reason codes")


def evaluate_holdout(evidence: HoldoutEvidence) -> HoldoutDecision:
    """Apply the frozen P1d rule; missing/weak evidence never passes.

    `pass_to_paper` means eligible to begin the paper promotion observation
    period. It does not activate a strategy or authorize live routing.
    """
    if evidence.timeframe not in {Timeframe.D1, Timeframe.M5}:
        raise ValueError("P1 holdout supports only daily and 5-minute candidates")
    if evidence.completed_trades < 0:
        raise ValueError("completed_trades must be non-negative")
    if evidence.family_size != P1_HOLDOUT_FAMILY_SIZE:
        raise ValueError("holdout correction must cover the frozen 15-variant P1 family")
    if evidence.instrument_count != P1_PILOT_INSTRUMENT_COUNT:
        raise ValueError("holdout must cover the fixed five-symbol pilot")
    if not 0 <= evidence.profitable_instruments <= evidence.instrument_count:
        raise ValueError("profitable instrument count is out of range")
    if evidence.time_block_count != P1_HOLDOUT_BLOCK_COUNT:
        raise ValueError("holdout must use the three predeclared chronological blocks")
    if not 0 <= evidence.profitable_time_blocks <= evidence.time_block_count:
        raise ValueError("profitable time-block count is out of range")
    for value in (
        evidence.mean_daily_excess_return_after_costs,
        evidence.bonferroni_adjusted_p_value,
        evidence.bootstrap_ci_lower_bound,
    ):
        if value is not None and not value.is_finite():
            raise ValueError("holdout evidence values must be finite")
    if evidence.bonferroni_adjusted_p_value is not None and not Decimal(
        0
    ) <= evidence.bonferroni_adjusted_p_value <= Decimal(1):
        raise ValueError("adjusted p-value must be in [0, 1]")

    minimum_trades = 60 if evidence.timeframe is Timeframe.M5 else 30
    missing: list[str] = []
    if not evidence.data_complete:
        missing.append("incomplete_data")
    if evidence.completed_trades < minimum_trades:
        missing.append(f"minimum_trades_not_met:{minimum_trades}")
    if (
        evidence.mean_daily_excess_return_after_costs is None
        or evidence.bonferroni_adjusted_p_value is None
        or evidence.bootstrap_ci_lower_bound is None
    ):
        missing.append("required_statistics_missing")
    if missing:
        return HoldoutDecision("inconclusive", tuple(missing))

    assert evidence.mean_daily_excess_return_after_costs is not None
    assert evidence.bonferroni_adjusted_p_value is not None
    assert evidence.bootstrap_ci_lower_bound is not None
    failures: list[str] = []
    if evidence.mean_daily_excess_return_after_costs <= 0:
        failures.append("mean_daily_excess_return_not_positive")
    if evidence.profitable_instruments < 3:
        failures.append("profitable_instruments_below_3_of_5")
    if evidence.profitable_time_blocks < 2:
        failures.append("profitable_time_blocks_below_2_of_3")
    if failures:
        return HoldoutDecision("rejected", tuple(failures))

    insufficient_statistical_evidence: list[str] = []
    if evidence.bonferroni_adjusted_p_value >= P1_FAMILY_ALPHA:
        insufficient_statistical_evidence.append("adjusted_p_value_not_below_0.05")
    if evidence.bootstrap_ci_lower_bound <= 0:
        insufficient_statistical_evidence.append("bootstrap_ci_includes_zero")
    if insufficient_statistical_evidence:
        return HoldoutDecision("inconclusive", tuple(insufficient_statistical_evidence))
    return HoldoutDecision("pass_to_paper", ("all_preregistered_gates_passed",))
