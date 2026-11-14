from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading.backtest.walk_forward import split_walk_forward
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
