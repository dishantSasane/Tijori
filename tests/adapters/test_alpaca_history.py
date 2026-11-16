import json
from datetime import UTC, datetime

import pytest

from trading.adapters.alpaca_history import AlpacaHistoryClient, AlpacaHistoryError
from trading.core.enums import MarketId, Timeframe

SAMPLE_BAR = {
    "t": "2024-01-02T00:00:00Z",
    "o": "100",
    "h": "110",
    "l": "90",
    "c": "105",
    "v": "1234",
}


def test_requires_key_pair() -> None:
    with pytest.raises(ValueError):
        AlpacaHistoryClient(key_id="", secret_key="x")


def test_rejects_non_us_equity_market() -> None:
    client = AlpacaHistoryClient(key_id="k", secret_key="s", requester=lambda *a, **k: b"{}")
    with pytest.raises(ValueError):
        client.fetch(
            "AAPL",
            symbol="AAPL",
            market=MarketId.CRYPTO,
            timeframe=Timeframe.D1,
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 2, tzinfo=UTC),
            ingest_ts=datetime(2024, 1, 3, tzinfo=UTC),
        )


def test_parses_daily_bars_and_sends_auth_headers() -> None:
    seen_headers: dict[str, str] = {}

    def fake_request(url: str, headers: dict[str, str]) -> bytes:
        seen_headers.update(headers)
        return json.dumps({"bars": {"AAPL": [SAMPLE_BAR]}, "next_page_token": None}).encode()

    client = AlpacaHistoryClient(key_id="k", secret_key="s", requester=fake_request)
    candles, next_token = client.fetch(
        "AAPL",
        symbol="AAPL",
        market=MarketId.US_EQUITY,
        timeframe=Timeframe.D1,
        start=datetime(2024, 1, 1, tzinfo=UTC),
        end=datetime(2024, 1, 3, tzinfo=UTC),
        ingest_ts=datetime(2024, 1, 3, tzinfo=UTC),
    )
    assert len(candles) == 1
    assert candles[0].source == "alpaca"
    assert str(candles[0].close) == "105"
    assert next_token is None
    assert seen_headers["APCA-API-KEY-ID"] == "k"
    assert seen_headers["APCA-API-SECRET-KEY"] == "s"


def test_raises_on_api_error_payload() -> None:
    client = AlpacaHistoryClient(
        key_id="k", secret_key="s", requester=lambda *a, **k: b'{"message": "forbidden"}'
    )
    with pytest.raises(AlpacaHistoryError):
        client.fetch(
            "AAPL",
            symbol="AAPL",
            market=MarketId.US_EQUITY,
            timeframe=Timeframe.D1,
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 2, tzinfo=UTC),
            ingest_ts=datetime(2024, 1, 3, tzinfo=UTC),
        )
