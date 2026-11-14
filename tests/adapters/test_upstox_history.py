import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from trading.adapters.upstox_history import UpstoxAccessError, UpstoxHistoryClient, _request
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


def test_request_has_explicit_application_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    class Response:
        def __enter__(self) -> object:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return b"{}"

    def fake_urlopen(request: Request, timeout: int) -> Response:
        captured.update(dict(request.headers))
        return Response()

    monkeypatch.setattr("trading.adapters.upstox_history.urlopen", fake_urlopen)
    _request("https://api.upstox.com", {})
    assert captured["Content-type"] == "application/json"
    assert captured["User-agent"] == "Tijori/0.0.1"


def test_provider_access_block_is_non_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    error = HTTPError("https://api.upstox.com", 403, "blocked", {}, None)

    def blocked(*args: object, **kwargs: object) -> object:
        raise error

    monkeypatch.setattr("trading.adapters.upstox_history.urlopen", blocked)
    with pytest.raises(UpstoxAccessError, match="do not retry"):
        _request("https://api.upstox.com", {})
