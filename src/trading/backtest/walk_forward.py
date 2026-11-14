"""Leakage-resistant walk-forward data partitioning."""

from __future__ import annotations

from datetime import datetime

from trading.core.models import Candle


def split_walk_forward(
    candles: list[Candle], split_at: datetime, *, embargo_bars: int = 1
) -> tuple[list[Candle], list[Candle]]:
    """Split closed candles while excluding next-open leakage at each edge."""
    if embargo_bars < 0:
        raise ValueError("embargo_bars must be non-negative")
    if any(
        left.ts_open_utc >= right.ts_open_utc
        for left, right in zip(candles, candles[1:], strict=False)
    ):
        raise ValueError("candles must be strictly ordered by open time")
    split_index = next(
        (index for index, candle in enumerate(candles) if candle.ts_open_utc >= split_at),
        len(candles),
    )
    in_sample = candles[: max(0, split_index - embargo_bars)]
    out_of_sample = candles[split_index : max(split_index, len(candles) - embargo_bars)]
    if not in_sample or not out_of_sample:
        raise ValueError("split must leave non-empty in-sample and out-of-sample windows")
    return in_sample, out_of_sample
