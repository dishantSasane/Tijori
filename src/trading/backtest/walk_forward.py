"""Leakage-resistant walk-forward data partitioning."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from trading.core.models import Candle


@dataclass(frozen=True)
class WalkForwardWindow:
    """Index ranges for one chronological train/test evaluation window."""

    train_start: int
    train_end: int
    test_start: int
    test_end: int


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


def rolling_walk_forward_windows(
    candles: list[Candle],
    *,
    train_bars: int,
    test_bars: int,
    step_bars: int | None = None,
    embargo_bars: int = 1,
) -> tuple[WalkForwardWindow, ...]:
    """Build expanding chronological train/test windows.

    The embargo sits between train and test because a signal fills on the
    next candle's open. Windows advance by ``step_bars``; by default they
    advance by one complete test window.
    """
    if train_bars <= 0 or test_bars <= 0:
        raise ValueError("train_bars and test_bars must be positive")
    if embargo_bars < 0:
        raise ValueError("embargo_bars must be non-negative")
    if step_bars is None:
        step_bars = test_bars
    if step_bars <= 0:
        raise ValueError("step_bars must be positive")
    if step_bars < test_bars:
        raise ValueError("step_bars must be at least test_bars to avoid overlapping tests")
    if any(
        left.ts_open_utc >= right.ts_open_utc
        for left, right in zip(candles, candles[1:], strict=False)
    ):
        raise ValueError("candles must be strictly ordered by open time")
    windows: list[WalkForwardWindow] = []
    test_start = train_bars + embargo_bars
    while test_start + test_bars <= len(candles):
        windows.append(
            WalkForwardWindow(
                train_start=0,
                train_end=test_start - embargo_bars,
                test_start=test_start,
                test_end=test_start + test_bars,
            )
        )
        test_start += step_bars
    if not windows:
        raise ValueError("not enough candles for one walk-forward window")
    return tuple(windows)
