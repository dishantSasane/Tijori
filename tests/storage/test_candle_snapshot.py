import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from trading.adapters.upstox_history import UpstoxHistoryClient
from trading.core.enums import MarketId, Timeframe
from trading.storage.candle_snapshot import candle_snapshot_sha256
from trading.storage.history_archive import save_history_snapshot


def save_response(directory: Path, symbol: str, key: str) -> Path:
    raw = b'{"status":"success","data":{"candles":[]}}'
    client = UpstoxHistoryClient(
        requester=lambda _url, _headers: raw,
        clock=lambda: datetime(2026, 11, 15, tzinfo=UTC),
    )
    snapshot = client.fetch_snapshot(
        key,
        symbol=symbol,
        market=MarketId.IN_EQUITY,
        timeframe=Timeframe.D1,
        from_date="2010-01-01",
        to_date="2015-12-31",
        ingest_ts=datetime(2026, 11, 15, tzinfo=UTC),
        access_token="fixture-only",
    )
    _, manifest_path = save_history_snapshot(snapshot, directory)
    return manifest_path


def test_candle_snapshot_hash_is_order_independent_and_window_specific(tmp_path: Path) -> None:
    reliance = save_response(tmp_path, "RELIANCE", "NSE_EQ|INE002A01018")
    infy = save_response(tmp_path, "INFY", "NSE_EQ|INE009A01021")
    forward = candle_snapshot_sha256(
        [reliance, infy], timeframe=Timeframe.D1, start="2010-01-01", end="2015-12-31"
    )
    reverse = candle_snapshot_sha256(
        [infy, reliance], timeframe=Timeframe.D1, start="2010-01-01", end="2015-12-31"
    )
    narrowed = candle_snapshot_sha256(
        [reliance, infy], timeframe=Timeframe.D1, start="2011-01-01", end="2015-12-31"
    )
    assert forward == reverse
    assert forward != narrowed


def test_candle_snapshot_rejects_corrupt_archived_response(tmp_path: Path) -> None:
    manifest = save_response(tmp_path, "RELIANCE", "NSE_EQ|INE002A01018")
    response_name = json.loads(manifest.read_text())["raw_response"]
    (tmp_path / response_name).write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        candle_snapshot_sha256(
            [manifest], timeframe=Timeframe.D1, start="2010-01-01", end="2015-12-31"
        )


def test_candle_snapshot_rejects_timeframe_mismatch(tmp_path: Path) -> None:
    manifest = save_response(tmp_path, "RELIANCE", "NSE_EQ|INE002A01018")
    with pytest.raises(ValueError, match="timeframe"):
        candle_snapshot_sha256(
            [manifest], timeframe=Timeframe.M5, start="2010-01-01", end="2015-12-31"
        )
