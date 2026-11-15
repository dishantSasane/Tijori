import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

from trading.storage.p1_resilient_intraday_fetch import (
    ResilientFetchError,
    fetch_intraday_chunk_skipping_malformed_rows,
    save_resilient_snapshot,
)


def fake_response(candles: list[list[object]]) -> bytes:
    return json.dumps({"status": "success", "data": {"candles": candles}}).encode("utf-8")


def test_malformed_row_is_excluded_but_raw_bytes_and_valid_rows_survive() -> None:
    good = ["2024-06-24T09:15:00+05:30", 835.0, 839.0, 834.0, 838.0, 1000, 0]
    bad = ["2024-06-25T09:15:00+05:30", 835.6, 839.8, 837.4, 839.6, 370096, 0]  # open < low
    raw = fake_response([good, bad])
    with patch("trading.storage.p1_resilient_intraday_fetch._request", return_value=raw) as mocked:
        result = fetch_intraday_chunk_skipping_malformed_rows(
            "NSE_EQ|INE040A01034",
            symbol="HDFCBANK",
            timeframe="1m",
            from_date="2024-06-01",
            to_date="2024-06-30",
            access_token="unused-fake-token",
            ingest_ts=datetime(2026, 1, 1, tzinfo=UTC),
        )
        mocked.assert_called_once()
    assert len(result.candles) == 1
    assert result.candles[0].open == Decimal("835.0")
    assert len(result.skipped_rows) == 1
    assert result.skipped_rows[0][0] == "2024-06-25T09:15:00+05:30"
    assert result.raw_response == raw  # every byte preserved, bad row included


def test_all_valid_rows_produces_no_skips() -> None:
    rows = [
        ["2024-06-24T09:15:00+05:30", 100, 101, 99, 100.5, 10, 0],
        ["2024-06-24T09:16:00+05:30", 100.5, 101.5, 99.5, 101, 20, 0],
    ]
    raw = fake_response(rows)
    with patch("trading.storage.p1_resilient_intraday_fetch._request", return_value=raw):
        result = fetch_intraday_chunk_skipping_malformed_rows(
            "NSE_EQ|INE040A01034",
            symbol="HDFCBANK",
            timeframe="1m",
            from_date="2024-06-01",
            to_date="2024-06-30",
            access_token="unused-fake-token",
        )
    assert len(result.candles) == 2
    assert result.skipped_rows == ()


def test_rejects_unsupported_timeframe() -> None:
    with pytest.raises(ValueError, match="unsupported intraday timeframe"):
        fetch_intraday_chunk_skipping_malformed_rows(
            "NSE_EQ|INE040A01034",
            symbol="HDFCBANK",
            timeframe="15m",
            from_date="2024-06-01",
            to_date="2024-06-30",
            access_token="unused-fake-token",
        )


def test_raises_on_api_error_status() -> None:
    raw = json.dumps({"status": "error"}).encode("utf-8")
    with patch("trading.storage.p1_resilient_intraday_fetch._request", return_value=raw):
        with pytest.raises(ResilientFetchError):
            fetch_intraday_chunk_skipping_malformed_rows(
                "NSE_EQ|INE040A01034",
                symbol="HDFCBANK",
                timeframe="1m",
                from_date="2024-06-01",
                to_date="2024-06-30",
                access_token="unused-fake-token",
            )


def test_save_resilient_snapshot_records_skipped_rows(tmp_path: Path) -> None:
    good = ["2024-06-24T09:15:00+05:30", 100, 101, 99, 100.5, 10, 0]
    bad = ["2024-06-25T09:15:00+05:30", 835.6, 839.8, 837.4, 839.6, 370096, 0]
    raw = fake_response([good, bad])
    with patch("trading.storage.p1_resilient_intraday_fetch._request", return_value=raw):
        result = fetch_intraday_chunk_skipping_malformed_rows(
            "NSE_EQ|INE040A01034",
            symbol="HDFCBANK",
            timeframe="1m",
            from_date="2024-06-01",
            to_date="2024-06-30",
            access_token="unused-fake-token",
        )
    raw_path, manifest_path = save_resilient_snapshot(result, tmp_path)
    assert raw_path.read_bytes() == raw
    manifest = json.loads(manifest_path.read_text())
    assert manifest["candle_count"] == 1
    assert len(manifest["skipped_rows"]) == 1
    assert manifest["skipped_rows"][0][0] == "2024-06-25T09:15:00+05:30"
