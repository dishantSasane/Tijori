from decimal import Decimal

import pytest

from trading.backtest.promotion import HoldoutDecision, HoldoutEvidence, evaluate_holdout
from trading.core.enums import Timeframe


def evidence(**changes: object) -> HoldoutEvidence:
    values: dict[str, object] = {
        "timeframe": Timeframe.D1,
        "completed_trades": 30,
        "family_size": 15,
        "mean_daily_excess_return_after_costs": Decimal("0.0008"),
        "bonferroni_adjusted_p_value": Decimal("0.03"),
        "bootstrap_ci_lower_bound": Decimal("0.01"),
        "profitable_instruments": 4,
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
        ({"profitable_instruments": 2}, "profitable_instruments_below_3_of_5"),
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
