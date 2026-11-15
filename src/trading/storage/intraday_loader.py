"""Resumable Upstox intraday history ingestion into the local candle store."""

from __future__ import annotations

import calendar
import os
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from trading.adapters.upstox_history import UpstoxHistoryClient
from trading.core.enums import MarketId, Timeframe
from trading.storage.adjusted_ingestion import append_adjusted_candles
from trading.storage.candles import CandleStore
from trading.storage.corporate_actions import ShareAdjustment

MAX_INTRADAY_RANGE = timedelta(days=31)
# Upstox documents a 2,000-request / 30-minute cap for this API. A 0.91s
# interval stays below that longer-window limit with a small safety margin.
DEFAULT_MINIMUM_REQUEST_INTERVAL_SECONDS = 0.91


@dataclass(frozen=True)
class Instrument:
    instrument_key: str
    symbol: str
    market: MarketId = MarketId.IN_EQUITY


@dataclass(frozen=True)
class IngestionSummary:
    requests: int
    fetched: int
    inserted: int


def runtime_access_token(environ: dict[str, str] | None = None) -> str:
    """Require a freshly supplied process token; never read .env or persist it."""
    values = os.environ if environ is None else environ
    token = values.get("UPSTOX_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "Set UPSTOX_ACCESS_TOKEN in the runtime environment using a fresh daily token"
        )
    return token


def _month_end(start: date) -> date:
    return date(start.year, start.month, calendar.monthrange(start.year, start.month)[1])


def iter_month_chunks(start: date, end: date) -> Iterable[tuple[date, date]]:
    """Yield inclusive calendar-month chunks, bounded by the provider's one-month cap."""
    if end < start:
        raise ValueError("end must be on or after start")
    cursor = start
    while cursor <= end:
        chunk_end = min(end, _month_end(cursor))
        if chunk_end - cursor > MAX_INTRADAY_RANGE:
            chunk_end = cursor + MAX_INTRADAY_RANGE
        yield cursor, chunk_end
        cursor = chunk_end + timedelta(days=1)


class UpstoxIntradayLoader:
    """Fetch historical intraday candles in bounded chunks and resume idempotently."""

    def __init__(
        self,
        *,
        client: UpstoxHistoryClient,
        store: CandleStore,
        access_token: str,
        clock: Callable[[], datetime],
        minimum_request_interval_seconds: float = DEFAULT_MINIMUM_REQUEST_INTERVAL_SECONDS,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if not access_token.strip():
            raise ValueError("access_token must not be empty")
        if minimum_request_interval_seconds < 0:
            raise ValueError("minimum request interval must be non-negative")
        self._client = client
        self._store = store
        self._access_token = access_token
        self._clock = clock
        self._minimum_interval = minimum_request_interval_seconds
        self._sleep = sleeper
        self._last_request_at: float | None = None

    def ingest(
        self,
        instruments: Iterable[Instrument],
        *,
        timeframe: Timeframe,
        start: date,
        end: date,
        action_ledger_complete: bool = False,
        adjustments: Iterable[ShareAdjustment] = (),
        adjustment_as_of: date | None = None,
        provider_adjusted_action_keys: set[tuple[str, date]]
        | frozenset[tuple[str, date]] = frozenset(),
    ) -> IngestionSummary:
        if timeframe not in {Timeframe.M1, Timeframe.M5}:
            raise ValueError("intraday P1 loader supports only 1-minute and 5-minute candles")
        if not action_ledger_complete:
            raise ValueError("a complete, authorized corporate-action ledger is required")
        action_ledger = tuple(adjustments)
        if adjustment_as_of is None:
            raise ValueError("adjustment_as_of is required for storage ingestion")
        chunks = tuple(iter_month_chunks(start, end))
        requests = fetched = inserted = 0
        for instrument in instruments:
            for chunk_start, chunk_end in chunks:
                self._wait_for_rate_limit()
                candles = self._client.fetch(
                    instrument.instrument_key,
                    symbol=instrument.symbol,
                    market=instrument.market,
                    timeframe=timeframe,
                    from_date=chunk_start.isoformat(),
                    to_date=chunk_end.isoformat(),
                    ingest_ts=self._clock().astimezone(UTC),
                    access_token=self._access_token,
                )
                requests += 1
                fetched += len(candles)
                inserted += append_adjusted_candles(
                    self._store,
                    candles,
                    action_ledger,
                    as_of=adjustment_as_of,
                    action_ledger_complete=action_ledger_complete,
                    provider_adjusted_action_keys=provider_adjusted_action_keys,
                )
        return IngestionSummary(requests=requests, fetched=fetched, inserted=inserted)

    def _wait_for_rate_limit(self) -> None:
        now = time.monotonic()
        if self._last_request_at is not None:
            remaining = self._minimum_interval - (now - self._last_request_at)
            if remaining > 0:
                self._sleep(remaining)
        self._last_request_at = time.monotonic()


def export_intraday_parquet(store_root: Path, output: Path) -> Path:
    """Export intraday rows from the shared store to a resumable Parquet snapshot."""
    output.parent.mkdir(parents=True, exist_ok=True)
    import duckdb

    connection = duckdb.connect(str(store_root / "candles.duckdb"), read_only=True)
    try:
        connection.execute(
            "COPY (SELECT * FROM candles WHERE timeframe IN ('1m', '5m') "
            "ORDER BY market, symbol, timeframe, ts_open_utc) TO ? (FORMAT PARQUET)",
            [str(output)],
        )
    finally:
        connection.close()
    with CandleStore(store_root) as store:
        store.write_adjustment_manifest(output)
    return output
