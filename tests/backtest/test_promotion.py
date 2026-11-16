from decimal import Decimal

import pytest

from trading.backtest.promotion import (
    HoldoutDecision,
    HoldoutEvidence,
    binomial_upper_tail_probability,
    evaluate_holdout,
    minimum_profitable_instruments_for_significance,
)
from trading.core.enums import Timeframe


def evidence(**changes: object) -> HoldoutEvidence:
    values: dict[str, object] = {
        "timeframe": Timeframe.D1,
        "completed_trades": 30,
        "family_size": 15,
        "mean_daily_excess_return_after_costs": Decimal("0.0008"),
        "bonferroni_adjusted_p_value": Decimal("0.03"),
        "bootstrap_ci_lower_bound": Decimal("0.01"),
        "profitable_instruments": 5,
        "instrument_count": 5,
        "profitable_time_blocks": 2,
        "time_block_count": 3,
        "data_complete": True,
    }
    values.update(changes)
    return HoldoutEvidence(**values)


def test_all_preregistered_gates_pass_before_paper_eligibility() -> None:
    decision = evaluate_holdout(evidence())
    assert decision.status == "pass_to_paper"
    assert decision.reasons == ("all_preregistered_gates_passed",)


def test_binomial_threshold_is_dynamic_and_uses_a_strict_one_sided_tail() -> None:
    """31/50 is close, but its P[X >= 31 | p=0.5] is still above 5%."""
    assert binomial_upper_tail_probability(31, 50) > Decimal("0.05")
    assert binomial_upper_tail_probability(32, 50) < Decimal("0.05")
    assert minimum_profitable_instruments_for_significance(50) == 32


def test_fifty_instrument_result_rejects_at_31_and_passes_at_32() -> None:
    rejected = evaluate_holdout(evidence(instrument_count=50, profitable_instruments=31))
    assert rejected.status == "rejected"
    assert rejected.reasons == ("profitable_instruments_binomial_p_value_not_below_0.05",)

    passed = evaluate_holdout(evidence(instrument_count=50, profitable_instruments=32))
    assert passed.status == "pass_to_paper"


def test_small_universe_without_a_significant_success_count_cannot_pass() -> None:
    decision = evaluate_holdout(evidence(instrument_count=1, profitable_instruments=1))
    assert decision.status == "rejected"
    assert decision.reasons == ("profitable_instruments_binomial_p_value_not_below_0.05",)


@pytest.mark.parametrize(
    ("timeframe", "trades", "minimum"),
    [(Timeframe.D1, 29, 30), (Timeframe.M5, 59, 60)],
)
def test_sample_below_frequency_specific_minimum_is_inconclusive(
    timeframe: Timeframe, trades: int, minimum: int
) -> None:
    decision = evaluate_holdout(evidence(timeframe=timeframe, completed_trades=trades))
    assert decision.status == "inconclusive"
    assert f"minimum_trades_not_met:{minimum}" in decision.reasons


def test_incomplete_data_cannot_pass_or_be_misreported_as_a_rejection() -> None:
    decision = evaluate_holdout(evidence(data_complete=False))
    assert decision.status == "inconclusive"
    assert decision.reasons == ("incomplete_data",)


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        (
            {"mean_daily_excess_return_after_costs": Decimal("0")},
            "mean_daily_excess_return_not_positive",
        ),
        (
            {"profitable_instruments": 4},
            "profitable_instruments_binomial_p_value_not_below_0.05",
        ),
        ({"profitable_time_blocks": 1}, "profitable_time_blocks_below_2_of_3"),
    ],
)
def test_material_holdout_failure_rejects_candidate(
    changes: dict[str, object], reason: str
) -> None:
    decision = evaluate_holdout(evidence(**changes))
    assert decision.status == "rejected"
    assert reason in decision.reasons


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        (
            {"bonferroni_adjusted_p_value": Decimal("0.05")},
            "adjusted_p_value_not_below_0.05",
        ),
        ({"bootstrap_ci_lower_bound": Decimal("0")}, "bootstrap_ci_includes_zero"),
    ],
)
def test_positive_but_uncertain_result_is_inconclusive(
    changes: dict[str, object], reason: str
) -> None:
    decision = evaluate_holdout(evidence(**changes))
    assert decision.status == "inconclusive"
    assert reason in decision.reasons


def test_uses_the_frozen_combined_family_size() -> None:
    with pytest.raises(ValueError, match="15-variant"):
        evaluate_holdout(evidence(family_size=18))


def test_invalid_p_value_is_rejected() -> None:
    with pytest.raises(ValueError, match=r"in \[0, 1\]"):
        evaluate_holdout(evidence(bonferroni_adjusted_p_value=Decimal("1.1")))


@pytest.mark.parametrize(
    ("status", "reasons"),
    [
        ("unknown", ("incomplete_data",)),
        ("rejected", ()),
        ("rejected", ("",)),
        ("rejected", ["incomplete_data"]),
    ],
)
def test_holdout_decision_rejects_untrusted_status_or_reason_data(
    status: str, reasons: object
) -> None:
    with pytest.raises(ValueError):
        HoldoutDecision(status, reasons)  # type: ignore[arg-type]
