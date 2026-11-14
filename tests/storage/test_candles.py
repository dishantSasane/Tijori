from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle
from trading.storage.candles import CandleStore, DuplicateCandleError


def candle(*, close: str = "105", ts: int = 0) -> Candle:
    return Candle(
        market=MarketId.IN_EQUITY,
        symbol="RELIANCE",
        timeframe=Timeframe.D1,
        ts_open_utc=datetime(2026, 1, 1 + ts, tzinfo=UTC),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("95"),
        close=Decimal(close),
        volume=Decimal("1000"),
        source="fixture",
        ingest_ts=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_append_is_idempotent_and_query_round_trips(tmp_path: Path) -> None:
    with CandleStore(tmp_path) as store:
        assert store.append([candle()]) == 1
        assert store.append([candle()]) == 0
        assert store.query(MarketId.IN_EQUITY, "RELIANCE", Timeframe.D1) == [candle()]


def test_conflicting_duplicate_is_rejected(tmp_path: Path) -> None:
    with CandleStore(tmp_path) as store:
        store.append([candle()])
        with pytest.raises(DuplicateCandleError):
            store.append([candle(close="106")])


def test_conflicting_batch_rolls_back_all_rows(tmp_path: Path) -> None:
    with CandleStore(tmp_path) as store:
        store.append([candle()])
        with pytest.raises(DuplicateCandleError):
            store.append([candle(ts=1), candle(close="106")])
        assert store.query(MarketId.IN_EQUITY, "RELIANCE", Timeframe.D1) == [candle()]


def test_query_filters_time_range_and_export_is_parquet(tmp_path: Path) -> None:
    output = tmp_path / "daily.parquet"
    with CandleStore(tmp_path) as store:
        store.append([candle(ts=0), candle(ts=1)])
        result = store.query(
            MarketId.IN_EQUITY,
            "RELIANCE",
            Timeframe.D1,
            start=datetime(2026, 1, 2, tzinfo=UTC),
        )
        assert [item.ts_open_utc for item in result] == [datetime(2026, 1, 2, tzinfo=UTC)]
        assert store.export_parquet(output) == output
        assert output.exists()


def test_load_parquet_round_trip_and_deduplicates(tmp_path: Path) -> None:
    output = tmp_path / "daily.parquet"
    with CandleStore(tmp_path / "source") as source:
        source.append([candle(ts=0), candle(ts=1)])
        source.export_parquet(output)

    with CandleStore(tmp_path / "loaded") as loaded:
        assert loaded.load_parquet(output) == 2
        assert loaded.load_parquet(output) == 0
        assert loaded.query(MarketId.IN_EQUITY, "RELIANCE", Timeframe.D1) == [
            candle(ts=0),
            candle(ts=1),
        ]
