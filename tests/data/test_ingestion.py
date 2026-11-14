import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from trading.adapters.upstox_history import UpstoxHistoryClient
from trading.core.enums import MarketId, Timeframe
from trading.data.ingestion import UpstoxHistoryRequest, ingest_upstox_history
from trading.storage.candles import CandleStore

FIXTURE = Path(__file__).parents[1] / "fixtures" / "upstox" / "nifty_daily.json"


def test_ingestion_archives_raw_response_and_is_idempotent(tmp_path: Path) -> None:
    payload = FIXTURE.read_bytes()

    def fake_request(*args: object, **kwargs: object) -> bytes:
        return payload

    request = UpstoxHistoryRequest(
        instrument_key="NSE_INDEX|Nifty 50",
        symbol="NIFTY 50",
        market=MarketId.IN_EQUITY,
        timeframe=Timeframe.D1,
        to_date="2025-01-02",
        from_date="2025-01-01",
        ingest_ts=datetime(2025, 1, 3, tzinfo=UTC),
        access_token="must-not-be-archived",
    )
    client = UpstoxHistoryClient(requester=fake_request)
    with CandleStore(tmp_path / "store") as store:
        first = ingest_upstox_history(
            request, client=client, store=store, archive_dir=tmp_path / "archive"
        )
        second = ingest_upstox_history(
            request, client=client, store=store, archive_dir=tmp_path / "archive"
        )
        candles = store.query(MarketId.IN_EQUITY, "NIFTY 50", Timeframe.D1)

    assert first.inserted_count == 2
    assert second.inserted_count == 0
    assert [candle.close for candle in candles] == [Decimal("23742.9"), Decimal("24188.65")]
    assert first.raw_path.read_bytes() == payload
    manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    assert manifest["raw_sha256"] == first.raw_sha256
    assert "must-not-be-archived" not in first.manifest_path.read_text(encoding="utf-8")
    assert manifest["ordering"] == "ascending_ts_open_utc"
