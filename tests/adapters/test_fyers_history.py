import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trading.adapters.fyers_history import FyersHistoryClient, FyersHistoryError
from trading.core.enums import MarketId, Timeframe


def _success_body(rows: list[list[object]]) -> bytes:
    return json.dumps({"s": "ok", "candles": rows}).encode("utf-8")


def test_fetch_parses_candles_and_sends_expected_headers() -> None:
    captured: dict[str, object] = {}

    def fake_requester(url: str, headers: dict[str, str]) -> bytes:
        captured["url"] = url
        captured["headers"] = headers
        return _success_body([[1735708800, "100", "110", "95", "105", "1000"]])

    client = FyersHistoryClient(
        app_id="FAKEAPPID",
        requester=fake_requester,
        clock=lambda: datetime(2026, 1, 1, 12, tzinfo=UTC),
    )
    candles = client.fetch(
        "NSE:RELIANCE-EQ",
        symbol="RELIANCE",
        market=MarketId.IN_EQUITY,
        timeframe=Timeframe.D1,
        range_from="2026-01-01",
        range_to="2026-01-02",
        access_token="fake-access-token",
        ingest_ts=datetime(2026, 1, 1, 12, tzinfo=UTC),
    )

    assert len(candles) == 1
    assert candles[0].close == Decimal("105")
    assert candles[0].source == "fyers"
    headers = captured["headers"]
    assert headers["Authorization"] == "FAKEAPPID:fake-access-token"
    assert "symbol=NSE%3ARELIANCE-EQ" in str(captured["url"])


def test_missing_access_token_fails_closed() -> None:
    client = FyersHistoryClient(app_id="FAKEAPPID", requester=lambda *a: b"")
    with pytest.raises(ValueError, match="access token"):
        client.fetch(
            "NSE:RELIANCE-EQ",
            symbol="RELIANCE",
            market=MarketId.IN_EQUITY,
            timeframe=Timeframe.D1,
            range_from="2026-01-01",
            range_to="2026-01-02",
            access_token="",
            ingest_ts=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_api_failure_status_raises() -> None:
    def fake_requester(url: str, headers: dict[str, str]) -> bytes:
        return json.dumps({"s": "error", "message": "bad token"}).encode("utf-8")

    client = FyersHistoryClient(app_id="FAKEAPPID", requester=fake_requester)
    with pytest.raises(FyersHistoryError):
        client.fetch(
            "NSE:RELIANCE-EQ",
            symbol="RELIANCE",
            market=MarketId.IN_EQUITY,
            timeframe=Timeframe.D1,
            range_from="2026-01-01",
            range_to="2026-01-02",
            access_token="fake-access-token",
            ingest_ts=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_empty_app_id_rejected_at_construction() -> None:
    with pytest.raises(ValueError, match="app_id"):
        FyersHistoryClient(app_id="  ", requester=lambda *a: b"")
