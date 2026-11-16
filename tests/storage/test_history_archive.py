import json
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from trading.adapters.upstox_history import UpstoxHistoryClient
from trading.core.enums import MarketId, Timeframe
from trading.storage.history_archive import save_history_snapshot


def snapshot():
    raw = b'{"status":"success","data":{"candles":[]}}'
    return UpstoxHistoryClient(
        requester=lambda _url, _headers: raw,
        clock=lambda: datetime(2026, 11, 15, tzinfo=UTC),
    ).fetch_snapshot(
        "NSE_EQ|INE002A01018",
        symbol="RELIANCE",
        market=MarketId.IN_EQUITY,
        timeframe=Timeframe.D1,
        from_date="2010-01-01",
        to_date="2015-12-31",
        ingest_ts=datetime(2026, 11, 15, tzinfo=UTC),
        access_token="fixture-only",
    )


def test_history_archive_is_content_addressed_and_idempotent(tmp_path) -> None:
    response = snapshot()
    raw_path, manifest_path = save_history_snapshot(response, tmp_path)
    assert raw_path.read_bytes() == response.raw_response
    assert manifest_path.exists()
    assert response.response_sha256 == sha256(response.raw_response).hexdigest()
    assert save_history_snapshot(response, tmp_path) == (raw_path, manifest_path)
    manifest = json.loads(manifest_path.read_text())
    assert manifest["first_candle_utc"] is None
    assert manifest["last_candle_utc"] is None


def test_history_archive_rejects_corrupt_existing_file(tmp_path) -> None:
    response = snapshot()
    raw_path, _ = save_history_snapshot(response, tmp_path)
    raw_path.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="corrupt"):
        save_history_snapshot(response, tmp_path)
