"""Small deterministic helpers for pre-registered candidate families."""

from __future__ import annotations

import random
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from pathlib import Path

P1_DAILY_FAMILY_SIZE = 15
"""T1/T2/T3/T4/T6, 3 variants each (P1_CANDIDATES.md)."""
P1_INTRADAY_FAMILY_SIZE = 3
"""T5 ORB, 3 target-multiple variants (P1_INTRADAY_CANDIDATES.md)."""
P1_FAMILY_SIZE = P1_DAILY_FAMILY_SIZE + P1_INTRADAY_FAMILY_SIZE
"""The single predeclared family (18) every Bonferroni correction uses.

Reporting daily and intraday results in separate tables is a presentation
choice -- group candidates by timeframe for display, but call
`bonferroni_adjust`/`p1_adjusted_p_value` with this combined size for every
candidate regardless of which table it's shown in. Two timeframe tables
sharing one family-wise correction is not the same claim as two independent
corrections (which would be looser, and not what P1_EVALUATION.md specifies).
"""


def validate_p1_family(catalog_path: Path) -> int:
    """Verify the machine-readable P1 hypothesis count matches this code version."""
    text = catalog_path.read_text(encoding="utf-8")
    section = text.split("## Machine-readable hypothesis family", maxsplit=1)[-1]
    block = section.split("```yaml", maxsplit=1)[1].split("```", maxsplit=1)[0]
    import yaml

    catalog = yaml.safe_load(block)
    families = catalog.get("strategy_families") if isinstance(catalog, dict) else None
    declared = catalog.get("hypothesis_count") if isinstance(catalog, dict) else None
    if not isinstance(families, dict) or not all(
        isinstance(value, int) and value >= 0 for value in families.values()
    ):
        raise ValueError("catalog strategy_families must map IDs to non-negative counts")
    actual = sum(families.values())
    if actual != declared or actual != P1_FAMILY_SIZE:
        raise ValueError("catalog hypothesis count differs from the frozen statistical family")
    return actual


def bonferroni_adjust(raw_p_value: Decimal, family_size: int) -> Decimal:
    """Return min(1, m*p) after strict input validation."""
    if not raw_p_value.is_finite() or not Decimal(0) <= raw_p_value <= Decimal(1):
        raise ValueError("p-value must be finite and in [0, 1]")
    if isinstance(family_size, bool) or not isinstance(family_size, int) or family_size <= 0:
        raise ValueError("family_size must be a positive integer")
    with localcontext() as context:
        context.prec = 50
        context.rounding = ROUND_HALF_EVEN
        return min(Decimal(1), raw_p_value * Decimal(family_size))


def synchronized_block_means(
    values: list[Decimal] | tuple[Decimal, ...],
    *,
    block_size: int,
    replicates: int,
    seed: int,
) -> list[Decimal]:
    """Sample non-circular moving blocks and return replicate means."""
    if not values or any(not value.is_finite() for value in values):
        raise ValueError("values must be a non-empty finite series")
    if (
        isinstance(block_size, bool)
        or not isinstance(block_size, int)
        or not 0 < block_size <= len(values)
    ):
        raise ValueError("block_size must be within the sample")
    if isinstance(replicates, bool) or not isinstance(replicates, int) or replicates <= 0:
        raise ValueError("replicates must be a positive integer")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    generator = random.Random(seed)
    means: list[Decimal] = []
    for _ in range(replicates):
        sample: list[Decimal] = []
        while len(sample) < len(values):
            start = generator.randint(0, len(values) - block_size)
            sample.extend(values[start : start + block_size])
        means.append(mean(sample[: len(values)]))
    return means


def mean(values: tuple[Decimal, ...] | list[Decimal]) -> Decimal:
    """Calculate an arithmetic mean with precision independent of caller context."""
    if not values:
        raise ValueError("mean requires at least one value")
    if any(not value.is_finite() for value in values):
        raise ValueError("mean values must be finite")
    tuples = [value.as_tuple() for value in values]
    max_digits = max(len(value_tuple.digits) for value_tuple in tuples)
    max_scale = max(
        (
            abs(value_tuple.exponent)
            for value_tuple in tuples
            if isinstance(value_tuple.exponent, int)
        ),
        default=0,
    )
    with localcontext() as context:
        context.prec = max(50, max_digits + max_scale + len(str(len(values))) + 4)
        context.rounding = ROUND_HALF_EVEN
        return sum(values, Decimal(0)) / Decimal(len(values))


def moving_block_excess_p_value(
    daily_returns: list[Decimal] | tuple[Decimal, ...],
    *,
    block_size: int = 20,
    replicates: int = 10_000,
    seed: int,
) -> Decimal:
    """One-sided bootstrap p-value for mean daily excess return > 0.

    Returns are centered under the null, then non-circular moving blocks are
    resampled using the same start bounds as the interval estimator. The
    plus-one correction prevents a reported zero p-value.
    """
    if not daily_returns or any(not value.is_finite() for value in daily_returns):
        raise ValueError("daily_returns must be a non-empty finite series")
    if (
        isinstance(block_size, bool)
        or not isinstance(block_size, int)
        or not 0 < block_size <= len(daily_returns)
    ):
        raise ValueError("block_size must be an integer within the sample length")
    if isinstance(replicates, bool) or not isinstance(replicates, int) or replicates <= 0:
        raise ValueError("replicates must be a positive integer")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    observed_mean = mean(daily_returns)
    centered = [value - observed_mean for value in daily_returns]
    replicate_means = synchronized_block_means(
        centered, block_size=block_size, replicates=replicates, seed=seed
    )
    exceedances = sum(value >= observed_mean for value in replicate_means)
    with localcontext() as context:
        context.prec = 50
        context.rounding = ROUND_HALF_EVEN
        return Decimal(exceedances + 1) / Decimal(replicates + 1)


def p1_adjusted_p_value(raw_p_value: Decimal) -> Decimal:
    """Apply the frozen 15-strategy hypothesis-family correction."""
    return bonferroni_adjust(raw_p_value, P1_FAMILY_SIZE)


def nearest_rank(values: list[Decimal], probability: Decimal) -> Decimal:
    if not values:
        raise ValueError("nearest-rank requires values")
    numerator, denominator = probability.as_integer_ratio()
    rank = max(1, (len(values) * numerator + denominator - 1) // denominator)
    return sorted(values)[rank - 1]
