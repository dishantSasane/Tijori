import json
from datetime import UTC, datetime
from pathlib import Path

from trading.adapters.alpaca_history import AlpacaHistoryClient
from trading.core.enums import MarketId, Timeframe
from trading.storage.candles import CandleStore
from trading.storage.us_equity_loader import load_history


def _bar(ts: datetime, close: str) -> dict[str, object]:
    return {"t": ts.isoformat(), "o": "100", "h": "110", "l": "90", "c": close, "v": "10"}


def test_loader_is_idempotent_and_resumes(tmp_path: Path) -> None:
    day0 = datetime(2024, 1, 1, tzinfo=UTC)
    day1 = datetime(2024, 1, 2, tzinfo=UTC)
    day2 = datetime(2024, 1, 3, tzinfo=UTC)

    calls: list[int] = []

    def fake_request(url: str, headers: dict[str, str]) -> bytes:
        calls.append(1)
        return json.dumps(
            {
                "bars": {"AAPL": [_bar(day0, "100"), _bar(day1, "101")]},
                "next_page_token": None,
            }
        ).encode()

    client = AlpacaHistoryClient(key_id="k", secret_key="s", requester=fake_request)
    store = CandleStore(tmp_path)
    try:
        inserted_first = load_history(
            client,
            store,
            alpaca_symbol="AAPL",
            symbol="AAPL",
            market=MarketId.US_EQUITY,
            timeframe=Timeframe.D1,
            start=day0,
            end=day2,
            sleep=lambda _: None,
        )
        assert inserted_first == 2
        assert len(calls) == 1

        # Resume: store already has day0/day1, loader should pick up from
        # the next step (day2), which the fake returns nothing new for -- so
        # the second call inserts 0 and does not re-request what's stored.
        def fake_request_second(url: str, headers: dict[str, str]) -> bytes:
            calls.append(1)
            return json.dumps({"bars": {"AAPL": []}, "next_page_token": None}).encode()

        client2 = AlpacaHistoryClient(key_id="k", secret_key="s", requester=fake_request_second)
        inserted_second = load_history(
            client2,
            store,
            alpaca_symbol="AAPL",
            symbol="AAPL",
            market=MarketId.US_EQUITY,
            timeframe=Timeframe.D1,
            start=day0,
            end=day2,
            sleep=lambda _: None,
        )
        assert inserted_second == 0
    finally:
        store.close()


def test_loader_follows_pagination_tokens(tmp_path: Path) -> None:
    day0 = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 1, 5, tzinfo=UTC)
    pages = [
        {"bars": {"AAPL": [_bar(day0, "100")]}, "next_page_token": "page2"},
        {"bars": {"AAPL": []}, "next_page_token": None},
    ]
    calls: list[int] = []

    def fake_request(url: str, headers: dict[str, str]) -> bytes:
        page = pages[len(calls)] if len(calls) < len(pages) else pages[-1]
        calls.append(1)
        return json.dumps(page).encode()

    client = AlpacaHistoryClient(key_id="k", secret_key="s", requester=fake_request)
    store = CandleStore(tmp_path)
    try:
        inserted = load_history(
            client,
            store,
            alpaca_symbol="AAPL",
            symbol="AAPL",
            market=MarketId.US_EQUITY,
            timeframe=Timeframe.D1,
            start=day0,
            end=end,
            sleep=lambda _: None,
        )
        assert inserted == 1
        assert len(calls) == 2
    finally:
        store.close()
