from decimal import ROUND_DOWN, Decimal, localcontext
from pathlib import Path

import pytest

from trading.backtest.multiple_testing import (
    P1_DAILY_FAMILY_SIZE,
    P1_FAMILY_SIZE,
    P1_INTRADAY_FAMILY_SIZE,
    bonferroni_adjust,
    mean,
    moving_block_excess_p_value,
    p1_adjusted_p_value,
    validate_p1_family,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


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
    # 12 daily (T1/T2/T4/T6, T3 deferred for the 5-symbol pilot) + 3 intraday
    # ORB -- catalog_version p1-daily-v2 in P1_CANDIDATES.md.
    assert P1_FAMILY_SIZE == 15
    assert P1_DAILY_FAMILY_SIZE + P1_INTRADAY_FAMILY_SIZE == P1_FAMILY_SIZE
    assert p1_adjusted_p_value(Decimal("0.01")) == Decimal("0.15")


def test_p1_family_size_matches_the_frozen_catalog_on_disk() -> None:
    """`validate_p1_family` existed but was never actually wired to check the
    real catalog -- its own unit tests only ever fed it a synthetic fixture
    matching whatever `P1_FAMILY_SIZE` already was, so a spec update (e.g. a
    new intraday family) and this constant could silently drift apart with
    nothing to catch it. This closes that gap: if `docs/specs/P1_CANDIDATES.md`
    ever declares a different hypothesis count than `P1_FAMILY_SIZE`, this
    test -- not a real backtest run -- is what fails first.
    """
    catalog_path = REPO_ROOT / "docs" / "specs" / "P1_CANDIDATES.md"
    assert validate_p1_family(catalog_path) == P1_FAMILY_SIZE


def test_moving_block_excess_test_is_deterministic_and_plus_one_corrected() -> None:
    values = [Decimal("0.001")] * 80
    first = moving_block_excess_p_value(values, block_size=10, replicates=200, seed=9)
    second = moving_block_excess_p_value(values, block_size=10, replicates=200, seed=9)
    assert first == second
    assert first > 0
    assert first <= 1


def test_moving_block_excess_p_value_known_answer_block_size_equals_sample() -> None:
    """Independent hand-derivation, not just self-consistency.

    When `block_size == len(values)` there is exactly one legal block start
    (`randint(0, len(values) - block_size)` collapses to `randint(0, 0)`), so
    every replicate is deterministically the whole centered series itself --
    true for ANY seed, since the random draw has only one possible outcome.
    Its mean is 0 by construction (mean-centering). So the exceedance count
    is fully hand-computable from the sign of the observed mean alone:
    - observed_mean > 0: 0 >= observed_mean is false for every replicate ->
      exceedances = 0 -> p = 1 / (replicates + 1).
    - observed_mean <= 0: 0 >= observed_mean is true for every replicate ->
      exceedances = replicates -> p = 1 (the plus-one-corrected maximum).
    """
    positive_mean_values = [Decimal("0.01"), Decimal("-0.01"), Decimal("0.02")]
    assert mean(positive_mean_values) > 0
    with localcontext() as context:
        context.prec = 50
        expected = Decimal(1) / Decimal(6)  # 1 / (5 + 1)
    for seed in (1, 2, 12345):  # the seed must not matter -- only one outcome exists.
        p = moving_block_excess_p_value(positive_mean_values, block_size=3, replicates=5, seed=seed)
        assert abs(p - expected) < Decimal("1e-30")

    zero_mean_values = [Decimal("0.01"), Decimal("-0.01")]
    assert mean(zero_mean_values) == 0
    p_zero = moving_block_excess_p_value(zero_mean_values, block_size=2, replicates=7, seed=99)
    assert p_zero == Decimal(1)
