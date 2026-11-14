import json
from datetime import UTC, datetime
from pathlib import Path

from trading.adapters.upstox_history import UpstoxHistoryClient
from trading.core.enums import MarketId, Timeframe

FIXTURES = Path(__file__).parents[1] / "fixtures" / "upstox"


def test_parses_daily_candles_and_converts_timestamps(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    payload = (FIXTURES / "nifty_daily.json").read_bytes()

    def fake_request(*args: object, **kwargs: object) -> bytes:
        return payload

    client = UpstoxHistoryClient(requester=fake_request)
    candles = client.fetch(
        "NSE_INDEX|Nifty 50",
        symbol="NIFTY 50",
        market=MarketId.IN_EQUITY,
        timeframe=Timeframe.D1,
        to_date="2025-01-02",
        from_date="2025-01-01",
        ingest_ts=datetime(2025, 1, 3, tzinfo=UTC),
    )
    assert len(candles) == 2
    assert candles[0].ts_open_utc.tzinfo is UTC
    assert str(candles[0].close) == "24188.65"


def test_empty_intraday_response_is_a_valid_empty_result(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    payload = json.loads((FIXTURES / "intraday_empty.json").read_text())

    def fake_request(*args: object, **kwargs: object) -> bytes:
        return json.dumps(payload).encode()

    candles = UpstoxHistoryClient(requester=fake_request).fetch(
        "NSE_INDEX|Nifty 50",
        symbol="NIFTY 50",
        market=MarketId.IN_EQUITY,
        timeframe=Timeframe.M1,
        to_date="2025-01-02",
        ingest_ts=datetime(2025, 1, 3, tzinfo=UTC),
    )
    assert candles == []
