import json
from datetime import UTC, datetime
from pathlib import Path

from trading.adapters.binance_history import BinanceHistoryClient
from trading.core.enums import MarketId, Timeframe
from trading.storage.candles import CandleStore
from trading.storage.crypto_loader import load_history


def _row(open_ms: int, close: str) -> list[object]:
    return [open_ms, "100", "110", "90", close, "10", open_ms + 999, "0", 0, "0", "0", "0"]


def test_loader_is_idempotent_and_resumes(tmp_path: Path) -> None:
    day0 = datetime(2024, 1, 1, tzinfo=UTC)
    day1 = datetime(2024, 1, 2, tzinfo=UTC)
    day2 = datetime(2024, 1, 3, tzinfo=UTC)

    calls: list[int] = []

    def fake_request(*args: object, **kwargs: object) -> bytes:
        calls.append(1)
        return json.dumps(
            [
                _row(int(day0.timestamp() * 1000), "100"),
                _row(int(day1.timestamp() * 1000), "101"),
            ]
        ).encode()

    client = BinanceHistoryClient(requester=fake_request)
    store = CandleStore(tmp_path)
    try:
        inserted_first = load_history(
            client,
            store,
            binance_symbol="BTCUSDT",
            symbol="BTCUSDT",
            market=MarketId.CRYPTO,
            timeframe=Timeframe.D1,
            start=day0,
            end=day2,
            sleep=lambda _: None,
        )
        assert inserted_first == 2

        # Re-running over the same window must not duplicate stored candles.
        def fake_request_again(*args: object, **kwargs: object) -> bytes:
            return b"[]"

        client_again = BinanceHistoryClient(requester=fake_request_again)
        inserted_second = load_history(
            client_again,
            store,
            binance_symbol="BTCUSDT",
            symbol="BTCUSDT",
            market=MarketId.CRYPTO,
            timeframe=Timeframe.D1,
            start=day0,
            end=day2,
            sleep=lambda _: None,
        )
        assert inserted_second == 0
        stored = store.query(MarketId.CRYPTO, "BTCUSDT", Timeframe.D1, start=day0, end=day2)
        assert len(stored) == 2
    finally:
        store.close()
