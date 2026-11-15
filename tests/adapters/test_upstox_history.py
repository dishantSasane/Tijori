import json
from datetime import UTC, datetime
from hashlib import sha256
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


def test_request_without_token_omits_authorization_header() -> None:
    calls: list[tuple[str, dict[str, str]]] = []

    def fake_request(url: str, headers: dict[str, str]) -> bytes:
        calls.append((url, headers))
        return b'{"status":"success","data":{"candles":[]}}'

    UpstoxHistoryClient(requester=fake_request).fetch(
        "NSE_INDEX|Nifty 50",
        symbol="NIFTY 50",
        market=MarketId.IN_EQUITY,
        timeframe=Timeframe.M1,
        to_date="2025-01-02",
        ingest_ts=datetime(2025, 1, 3, tzinfo=UTC),
    )
    assert calls[0][0].endswith("/intraday/NSE_INDEX%7CNifty%2050/minutes/1")
    assert "Authorization" not in calls[0][1]


def test_historical_intraday_request_uses_date_bounded_historical_endpoint() -> None:
    calls: list[str] = []

    def fake_request(url: str, headers: dict[str, str]) -> bytes:
        calls.append(url)
        return b'{"status":"success","data":{"candles":[]}}'

    UpstoxHistoryClient(requester=fake_request).fetch(
        "NSE_EQ|TEST",
        symbol="TEST",
        market=MarketId.IN_EQUITY,
        timeframe=Timeframe.M1,
        from_date="2026-10-01",
        to_date="2026-10-31",
        ingest_ts=datetime(2026, 11, 1, tzinfo=UTC),
    )

    assert calls == [
        "https://api.upstox.com/v3/historical-candle/NSE_EQ%7CTEST/minutes/1/2026-10-31/2026-10-01"
    ]


def test_history_snapshot_preserves_exact_response_hash_and_request() -> None:
    payload = (FIXTURES / "nifty_daily.json").read_bytes()
    retrieved = datetime(2026, 11, 15, 17, 0, tzinfo=UTC)
    client = UpstoxHistoryClient(
        requester=lambda _url, _headers: payload,
        clock=lambda: retrieved,
    )
    snapshot = client.fetch_snapshot(
        "NSE_INDEX|Nifty 50",
        symbol="NIFTY 50",
        market=MarketId.IN_EQUITY,
        timeframe=Timeframe.D1,
        from_date="2010-01-01",
        to_date="2015-12-31",
        ingest_ts=retrieved,
    )
    assert snapshot.raw_response == payload
    assert snapshot.response_sha256 == sha256(payload).hexdigest()
    assert snapshot.from_date == "2010-01-01"
    assert snapshot.to_date == "2015-12-31"
    assert snapshot.retrieved_at_utc == retrieved
    assert len(snapshot.candles) == 2
