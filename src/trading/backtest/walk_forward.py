"""Leakage-resistant walk-forward data partitioning."""

from __future__ import annotations

from datetime import datetime

from trading.core.models import Candle


def split_walk_forward(
    candles: list[Candle], split_at: datetime
) -> tuple[list[Candle], list[Candle]]:
    """Split closed candles into `[start, split)` and `[split, end)` windows."""
    if any(
        left.ts_open_utc >= right.ts_open_utc
        for left, right in zip(candles, candles[1:], strict=False)
    ):
        raise ValueError("candles must be strictly ordered by open time")
    in_sample = [candle for candle in candles if candle.ts_open_utc < split_at]
    out_of_sample = [candle for candle in candles if candle.ts_open_utc >= split_at]
    if not in_sample or not out_of_sample:
        raise ValueError("split must leave non-empty in-sample and out-of-sample windows")
    return in_sample, out_of_sample
