import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trading.adapters.angelone_history import AngelOneHistoryClient, AngelOneHistoryError
from trading.core.enums import MarketId, Timeframe


def _success_body(rows: list[list[object]]) -> bytes:
    return json.dumps({"status": True, "data": rows}).encode("utf-8")


def test_fetch_parses_candles_and_sends_expected_headers() -> None:
    captured: dict[str, object] = {}

    def fake_requester(url: str, headers: dict[str, str], body: bytes) -> bytes:
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = json.loads(body.decode("utf-8"))
        return _success_body([["2026-01-01T09:15:00+05:30", "100", "110", "95", "105", "1000"]])

    client = AngelOneHistoryClient(
        api_key="fake-api-key",
        requester=fake_requester,
        clock=lambda: datetime(2026, 1, 1, 12, tzinfo=UTC),
    )
    candles = client.fetch(
        "3045",
        symbol="RELIANCE",
        market=MarketId.IN_EQUITY,
        timeframe=Timeframe.D1,
        exchange="NSE",
        from_date="2026-01-01 09:00",
        to_date="2026-01-01 16:00",
        access_token="fake-session-token",
        ingest_ts=datetime(2026, 1, 1, 12, tzinfo=UTC),
    )

    assert len(candles) == 1
    assert candles[0].close == Decimal("105")
    assert candles[0].source == "angelone"
    headers = captured["headers"]
    assert headers["X-PrivateKey"] == "fake-api-key"
    assert headers["Authorization"] == "Bearer fake-session-token"
    body = captured["body"]
    assert body["symboltoken"] == "3045"
    assert body["interval"] == "ONE_DAY"


def test_missing_access_token_fails_closed() -> None:
    client = AngelOneHistoryClient(api_key="fake-api-key", requester=lambda *a: b"")
    with pytest.raises(ValueError, match="session access token"):
        client.fetch(
            "3045",
            symbol="RELIANCE",
            market=MarketId.IN_EQUITY,
            timeframe=Timeframe.D1,
            exchange="NSE",
            from_date="2026-01-01 09:00",
            to_date="2026-01-01 16:00",
            access_token="",
            ingest_ts=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_api_failure_status_raises() -> None:
    def fake_requester(url: str, headers: dict[str, str], body: bytes) -> bytes:
        return json.dumps({"status": False, "message": "bad token"}).encode("utf-8")

    client = AngelOneHistoryClient(api_key="fake-api-key", requester=fake_requester)
    with pytest.raises(AngelOneHistoryError):
        client.fetch(
            "3045",
            symbol="RELIANCE",
            market=MarketId.IN_EQUITY,
            timeframe=Timeframe.D1,
            exchange="NSE",
            from_date="2026-01-01 09:00",
            to_date="2026-01-01 16:00",
            access_token="fake-session-token",
            ingest_ts=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_empty_api_key_rejected_at_construction() -> None:
    with pytest.raises(ValueError, match="API key"):
        AngelOneHistoryClient(api_key="   ", requester=lambda *a: b"")
