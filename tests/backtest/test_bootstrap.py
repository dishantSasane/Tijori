from decimal import ROUND_DOWN, Decimal, localcontext

import pytest

from trading.backtest.bootstrap import moving_block_mean_interval


def test_bootstrap_is_deterministic_and_records_method() -> None:
    returns = [Decimal(index % 7 - 3) / Decimal(100) for index in range(100)]
    first = moving_block_mean_interval(returns, block_size=5, replicates=300, seed=42)
    second = moving_block_mean_interval(returns, block_size=5, replicates=300, seed=42)

    assert first == second
    assert first.sample_count == 100
    assert first.block_size == 5
    assert first.replicates == 300
    assert first.seed == 42
    assert first.quantile_method == "nearest-rank"
    assert first.lower <= first.upper


def test_constant_returns_have_degenerate_interval() -> None:
    interval = moving_block_mean_interval(
        [Decimal("0.01")] * 40, block_size=10, replicates=100, seed=1
    )
    assert interval.lower == Decimal("0.01")
    assert interval.upper == Decimal("0.01")


def test_bootstrap_interval_ignores_ambient_decimal_context() -> None:
    values = [Decimal(index) / Decimal(1000) for index in range(60)]
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_DOWN
        low_precision = moving_block_mean_interval(values, block_size=5, replicates=200, seed=4)
    standard = moving_block_mean_interval(values, block_size=5, replicates=200, seed=4)
    assert low_precision == standard


@pytest.mark.parametrize(
    "kwargs",
    [
        {"block_size": 0},
        {"block_size": 5},
        {"replicates": 0},
        {"seed": True},
    ],
)
def test_bootstrap_rejects_invalid_parameters(kwargs: dict[str, object]) -> None:
    arguments: dict[str, object] = {
        "block_size": 2,
        "replicates": 20,
        "seed": 3,
    }
    arguments.update(kwargs)
    with pytest.raises(ValueError):
        moving_block_mean_interval(
            [Decimal(0)] * 4,
            block_size=arguments["block_size"],  # type: ignore[arg-type]
            replicates=arguments["replicates"],  # type: ignore[arg-type]
            seed=arguments["seed"],  # type: ignore[arg-type]
        )


def test_bootstrap_rejects_non_finite_and_empty_returns() -> None:
    with pytest.raises(ValueError):
        moving_block_mean_interval([], block_size=1, seed=1)
    with pytest.raises(ValueError):
        moving_block_mean_interval([Decimal("NaN"), Decimal(0)], block_size=1, seed=1)
