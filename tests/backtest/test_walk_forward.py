from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading.backtest.walk_forward import (
    WalkForwardWindow,
    rolling_walk_forward_windows,
    split_walk_forward,
)
from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle


def bars() -> list[Candle]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Candle(
            market=MarketId.IN_EQUITY,
            symbol="TEST",
            timeframe=Timeframe.D1,
            ts_open_utc=start + timedelta(days=index),
            open=Decimal("10"),
            high=Decimal("11"),
            low=Decimal("9"),
            close=Decimal("10"),
            volume=Decimal("1"),
            source="test",
            ingest_ts=start,
        )
        for index in range(4)
    ]


def test_split_is_half_open_and_non_overlapping() -> None:
    in_sample, out_of_sample = split_walk_forward(
        bars(), datetime(2026, 1, 3, tzinfo=UTC), embargo_bars=0
    )
    assert len(in_sample) == 2
    assert len(out_of_sample) == 2
    assert in_sample[-1].ts_open_utc < out_of_sample[0].ts_open_utc


def test_split_rejects_unsorted_or_empty_windows() -> None:
    data = bars()
    with pytest.raises(ValueError, match="ordered"):
        split_walk_forward([data[1], data[0], *data[2:]], datetime(2026, 1, 3, tzinfo=UTC))
    with pytest.raises(ValueError, match="non-empty"):
        split_walk_forward(data, datetime(2025, 1, 1, tzinfo=UTC))


def test_split_applies_embargo_at_both_window_edges() -> None:
    in_sample, out_of_sample = split_walk_forward(
        bars(), datetime(2026, 1, 3, tzinfo=UTC), embargo_bars=1
    )
    assert [candle.ts_open_utc.day for candle in in_sample] == [1]
    assert [candle.ts_open_utc.day for candle in out_of_sample] == [3]


def test_rolling_windows_are_expanding_and_embargoed() -> None:
    windows = rolling_walk_forward_windows(
        bars(), train_bars=1, test_bars=1, step_bars=1, embargo_bars=1
    )
    assert windows == (
        WalkForwardWindow(train_start=0, train_end=1, test_start=2, test_end=3),
        WalkForwardWindow(train_start=0, train_end=2, test_start=3, test_end=4),
    )


def test_rolling_windows_require_enough_data() -> None:
    with pytest.raises(ValueError, match="not enough"):
        rolling_walk_forward_windows(bars(), train_bars=3, test_bars=2)


def test_rolling_windows_reject_overlapping_tests() -> None:
    with pytest.raises(ValueError, match="overlapping"):
        rolling_walk_forward_windows(bars(), train_bars=1, test_bars=2, step_bars=1)
