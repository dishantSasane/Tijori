"""Deterministic moving-block bootstrap for daily portfolio returns."""

from __future__ import annotations

import random
from decimal import Decimal
from typing import NamedTuple

from trading.backtest.multiple_testing import mean, nearest_rank


class BootstrapInterval(NamedTuple):
    lower: Decimal
    upper: Decimal
    sample_count: int
    block_size: int
    replicates: int
    seed: int
    quantile_method: str


def moving_block_mean_interval(
    daily_returns: list[Decimal] | tuple[Decimal, ...],
    *,
    block_size: int = 20,
    replicates: int = 10_000,
    seed: int,
) -> BootstrapInterval:
    """Estimate a two-sided 95% interval for mean daily return.

    Returns must contain one finite value per consecutive verified exchange
    session; callers encode flat sessions as explicit zero values.
    """
    if not daily_returns:
        raise ValueError("daily_returns must not be empty")
    if any(not value.is_finite() for value in daily_returns):
        raise ValueError("daily returns must be finite")
    if isinstance(block_size, bool) or not isinstance(block_size, int) or block_size <= 0:
        raise ValueError("block_size must be a positive integer")
    if isinstance(replicates, bool) or not isinstance(replicates, int) or replicates <= 0:
        raise ValueError("replicates must be a positive integer")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if block_size > len(daily_returns):
        raise ValueError("block_size cannot exceed the return sample length")

    generator = random.Random(seed)
    last_start = len(daily_returns) - block_size
    replicate_means: list[Decimal] = []
    for _ in range(replicates):
        sample: list[Decimal] = []
        while len(sample) < len(daily_returns):
            start = generator.randint(0, last_start)
            sample.extend(daily_returns[start : start + block_size])
        replicate_means.append(mean(sample[: len(daily_returns)]))

    return BootstrapInterval(
        lower=nearest_rank(replicate_means, Decimal("0.025")),
        upper=nearest_rank(replicate_means, Decimal("0.975")),
        sample_count=len(daily_returns),
        block_size=block_size,
        replicates=replicates,
        seed=seed,
        quantile_method="nearest-rank",
    )
