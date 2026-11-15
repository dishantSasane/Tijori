from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from trading.adapters.upstox_history import UpstoxHistoryClient
from trading.core.enums import MarketId, Timeframe
from trading.storage.candles import CandleStore
from trading.storage.corporate_actions import ShareAdjustment
from trading.storage.intraday_loader import (
    Instrument,
    UpstoxIntradayLoader,
    export_intraday_parquet,
    iter_month_chunks,
    runtime_access_token,
)


def test_runtime_token_requires_fresh_environment_value_and_never_reads_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("UPSTOX_ACCESS_TOKEN=stale-token\n")
    with pytest.raises(RuntimeError, match="fresh daily token"):
        runtime_access_token({})
    assert runtime_access_token({"UPSTOX_ACCESS_TOKEN": "today-token"}) == "today-token"


def test_month_chunks_are_inclusive_and_bounded() -> None:
    assert list(iter_month_chunks(date(2026, 10, 1), date(2026, 11, 13))) == [
        (date(2026, 10, 1), date(2026, 10, 31)),
        (date(2026, 11, 1), date(2026, 11, 13)),
    ]


def test_loader_resumes_idempotently_and_exports_intraday_parquet(tmp_path: Path) -> None:
    calls: list[tuple[str, dict[str, str]]] = []

    def fake_request(url: str, headers: dict[str, str]) -> bytes:
        calls.append((url, headers))
        return (
            b'{"status":"success","data":{"candles":['
            b'["2026-11-13T09:15:00+05:30",100,101,99,100.5,25,0]]}}'
        )

    client = UpstoxHistoryClient(requester=fake_request)
    instrument = Instrument("NSE_EQ|TEST", "TEST")
    now = datetime(2026, 11, 14, tzinfo=UTC)
    with CandleStore(tmp_path / "store") as store:
        loader = UpstoxIntradayLoader(
            client=client,
            store=store,
            access_token="one-time-test-token",
            clock=lambda: now,
            minimum_request_interval_seconds=0,
        )
        first = loader.ingest(
            [instrument],
            timeframe=Timeframe.M1,
            start=date(2026, 11, 13),
            end=date(2026, 11, 13),
            action_ledger_complete=True,
            adjustment_as_of=date(2026, 11, 13),
        )
        second = loader.ingest(
            [instrument],
            timeframe=Timeframe.M1,
            start=date(2026, 11, 13),
            end=date(2026, 11, 13),
            action_ledger_complete=True,
            adjustment_as_of=date(2026, 11, 13),
        )
        assert first.fetched == 1 and first.inserted == 1
        assert second.fetched == 1 and second.inserted == 0
        assert calls[0][1]["Authorization"] == "Bearer one-time-test-token"
        assert len(store.query(MarketId.IN_EQUITY, "TEST", Timeframe.M1)) == 1

    parquet = export_intraday_parquet(tmp_path / "store", tmp_path / "out" / "intraday.parquet")
    assert parquet.exists()
    with CandleStore(tmp_path / "loaded") as restored:
        assert restored.load_parquet(parquet) == 1
        assert restored.query(MarketId.IN_EQUITY, "TEST", Timeframe.M1)[0].close == 100.5


def test_loader_applies_action_adjustment_before_storage(tmp_path: Path) -> None:
    def fake_request(url: str, headers: dict[str, str]) -> bytes:
        return (
            b'{"status":"success","data":{"candles":['
            b'["2024-01-01T09:15:00+05:30",100,101,99,100.5,25,0]]}}'
        )

    client = UpstoxHistoryClient(requester=fake_request)
    action = ShareAdjustment(
        action_id="synthetic-split-notice",
        event_id="test-split-2024-01-02",
        revision=1,
        market=MarketId.IN_EQUITY,
        symbol="TEST",
        kind="split",
        published_date=date(2024, 1, 1),
        effective_date=date(2024, 1, 2),
        new_shares_per_old_share=Decimal("2"),
        source_ref="synthetic-known-answer",
    )
    with CandleStore(tmp_path / "store") as store:
        loader = UpstoxIntradayLoader(
            client=client,
            store=store,
            access_token="test-only-token",
            clock=lambda: datetime(2024, 1, 3, tzinfo=UTC),
            minimum_request_interval_seconds=0,
        )
        loader.ingest(
            [Instrument("NSE_EQ|TEST", "TEST")],
            timeframe=Timeframe.M1,
            start=date(2024, 1, 1),
            end=date(2024, 1, 1),
            action_ledger_complete=True,
            adjustments=[action],
            adjustment_as_of=date(2024, 1, 3),
        )
        stored = store.query(MarketId.IN_EQUITY, "TEST", Timeframe.M1)[0]

    assert stored.close == Decimal("50.25")
    assert stored.volume == Decimal("50")
    assert stored.adj_factor == Decimal("0.5")


def test_loader_requires_complete_action_ledger(tmp_path: Path) -> None:
    client = UpstoxHistoryClient(requester=lambda _url, _headers: b'{"data":{"candles":[]}}')
    action = ShareAdjustment(
        action_id="synthetic-action",
        event_id="event",
        revision=1,
        market=MarketId.IN_EQUITY,
        symbol="TEST",
        kind="split",
        published_date=date(2024, 1, 1),
        effective_date=date(2024, 1, 2),
        new_shares_per_old_share=Decimal("2"),
        source_ref="synthetic-known-answer",
    )
    with CandleStore(tmp_path / "store") as store:
        loader = UpstoxIntradayLoader(
            client=client,
            store=store,
            access_token="test-only-token",
            clock=lambda: datetime(2024, 1, 3, tzinfo=UTC),
            minimum_request_interval_seconds=0,
        )
        with pytest.raises(ValueError, match="complete, authorized corporate-action ledger"):
            loader.ingest(
                [Instrument("NSE_EQ|TEST", "TEST")],
                timeframe=Timeframe.M1,
                start=date(2024, 1, 1),
                end=date(2024, 1, 1),
                adjustments=[action],
            )


def test_loader_requires_as_of_date_for_complete_action_ledger(tmp_path: Path) -> None:
    client = UpstoxHistoryClient(requester=lambda _url, _headers: b'{"data":{"candles":[]}}')
    with CandleStore(tmp_path / "store") as store:
        loader = UpstoxIntradayLoader(
            client=client,
            store=store,
            access_token="test-only-token",
            clock=lambda: datetime(2024, 1, 3, tzinfo=UTC),
            minimum_request_interval_seconds=0,
        )
        with pytest.raises(ValueError, match="adjustment_as_of is required"):
            loader.ingest(
                [Instrument("NSE_EQ|TEST", "TEST")],
                timeframe=Timeframe.M1,
                start=date(2024, 1, 1),
                end=date(2024, 1, 1),
                action_ledger_complete=True,
            )
