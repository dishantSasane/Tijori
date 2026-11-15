import json
from datetime import UTC, datetime

import pytest

from trading.adapters.binance_history import BinanceHistoryClient, BinanceHistoryError
from trading.core.enums import MarketId, Timeframe

SAMPLE_ROW = [
    1700000000000,
    "100.00000000",
    "110.00000000",
    "90.00000000",
    "105.00000000",
    "1234.56000000",
    1700000059999,
    "0",
    0,
    "0",
    "0",
    "0",
]


def test_parses_daily_candles() -> None:
    def fake_request(*args: object, **kwargs: object) -> bytes:
        return json.dumps([SAMPLE_ROW]).encode()

    client = BinanceHistoryClient(requester=fake_request)
    candles = client.fetch(
        "BTCUSDT",
        symbol="BTCUSDT",
        market=MarketId.CRYPTO,
        timeframe=Timeframe.D1,
        ingest_ts=datetime(2025, 1, 3, tzinfo=UTC),
    )
    assert len(candles) == 1
    assert candles[0].ts_open_utc.tzinfo is UTC
    assert str(candles[0].close) == "105.00000000"
    assert candles[0].source == "binance"


def test_empty_response_is_a_valid_empty_result() -> None:
    def fake_request(*args: object, **kwargs: object) -> bytes:
        return b"[]"

    candles = BinanceHistoryClient(requester=fake_request).fetch(
        "BTCUSDT",
        symbol="BTCUSDT",
        market=MarketId.CRYPTO,
        timeframe=Timeframe.M1,
        ingest_ts=datetime(2025, 1, 3, tzinfo=UTC),
    )
    assert candles == []


def test_rejects_non_crypto_market() -> None:
    client = BinanceHistoryClient(requester=lambda *a, **k: b"[]")
    with pytest.raises(ValueError, match="crypto/memecoin only"):
        client.fetch(
            "BTCUSDT",
            symbol="BTCUSDT",
            market=MarketId.IN_EQUITY,
            timeframe=Timeframe.D1,
            ingest_ts=datetime(2025, 1, 3, tzinfo=UTC),
        )


def test_error_payload_raises() -> None:
    def fake_request(*args: object, **kwargs: object) -> bytes:
        return json.dumps({"code": -1121, "msg": "Invalid symbol."}).encode()

    client = BinanceHistoryClient(requester=fake_request)
    with pytest.raises(BinanceHistoryError):
        client.fetch(
            "NOPE",
            symbol="NOPE",
            market=MarketId.CRYPTO,
            timeframe=Timeframe.D1,
            ingest_ts=datetime(2025, 1, 3, tzinfo=UTC),
        )


def test_limit_out_of_range_rejected() -> None:
    client = BinanceHistoryClient(requester=lambda *a, **k: b"[]")
    with pytest.raises(ValueError, match="limit must be in"):
        client.fetch(
            "BTCUSDT",
            symbol="BTCUSDT",
            market=MarketId.CRYPTO,
            timeframe=Timeframe.D1,
            ingest_ts=datetime(2025, 1, 3, tzinfo=UTC),
            limit=1001,
        )
