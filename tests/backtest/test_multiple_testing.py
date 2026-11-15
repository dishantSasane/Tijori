from decimal import ROUND_DOWN, Decimal, localcontext

import pytest

from trading.backtest.multiple_testing import (
    P1_FAMILY_SIZE,
    bonferroni_adjust,
    mean,
    moving_block_excess_p_value,
    p1_adjusted_p_value,
)


@pytest.mark.parametrize(
    ("p_value", "family_size", "expected"),
    [
        (Decimal("0.01"), 15, Decimal("0.15")),
        (Decimal("0.1"), 15, Decimal("1")),
        (Decimal("0"), 1, Decimal("0")),
    ],
)
def test_bonferroni_adjustment(p_value: Decimal, family_size: int, expected: Decimal) -> None:
    assert bonferroni_adjust(p_value, family_size) == expected


@pytest.mark.parametrize(
    ("p_value", "family_size"),
    [(Decimal("-0.1"), 3), (Decimal("1.1"), 3), (Decimal("NaN"), 3), (Decimal("0.1"), True)],
)
def test_bonferroni_rejects_invalid_inputs(p_value: Decimal, family_size: int) -> None:
    with pytest.raises(ValueError):
        bonferroni_adjust(p_value, family_size)


def test_mean_is_independent_of_decimal_context_precision() -> None:
    with localcontext() as context:
        context.prec = 3
        result = mean([Decimal("100000000000000001"), Decimal("100000000000000000")])
    assert result == Decimal("100000000000000000.5")


@pytest.mark.parametrize("precision,rounding", [(2, ROUND_DOWN), (50, "ROUND_HALF_UP")])
def test_mean_ignores_ambient_precision_and_rounding(precision: int, rounding: str) -> None:
    with localcontext() as context:
        context.prec = precision
        context.rounding = rounding
        result = mean([Decimal("1"), Decimal("0"), Decimal("0")])
    with localcontext() as context:
        context.prec = 50
        expected = mean([Decimal("1"), Decimal("0"), Decimal("0")])
    assert result == expected


def test_mean_rejects_empty_or_non_finite_values() -> None:
    with pytest.raises(ValueError):
        mean([])
    with pytest.raises(ValueError):
        mean([Decimal("Infinity")])


def test_frozen_family_size_and_adjusted_p_value() -> None:
    assert P1_FAMILY_SIZE == 15
    assert p1_adjusted_p_value(Decimal("0.01")) == Decimal("0.15")


def test_moving_block_excess_test_is_deterministic_and_plus_one_corrected() -> None:
    values = [Decimal("0.001")] * 80
    first = moving_block_excess_p_value(values, block_size=10, replicates=200, seed=9)
    second = moving_block_excess_p_value(values, block_size=10, replicates=200, seed=9)
    assert first == second
    assert first > 0
    assert first <= 1
