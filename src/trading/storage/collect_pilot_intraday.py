"""Archive resumable raw Upstox M1/M5 snapshots for the five-symbol P1 pilot."""

from __future__ import annotations

import argparse
import getpass
import time
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path

from trading.adapters.upstox_history import UpstoxHistoryClient
from trading.core.enums import MarketId, Timeframe
from trading.storage.collect_pilot_daily import PILOT_INSTRUMENTS
from trading.storage.history_archive import find_history_snapshot, save_history_snapshot
from trading.storage.intraday_loader import (
    DEFAULT_MINIMUM_REQUEST_INTERVAL_SECONDS,
    iter_month_chunks,
)

INTRADAY_START = date(2022, 1, 1)


def collect_pilot_intraday(
    *,
    access_token: str,
    start: date,
    end: date,
    output: Path,
    minimum_request_interval_seconds: float = DEFAULT_MINIMUM_REQUEST_INTERVAL_SECONDS,
    sleeper: Callable[[float], None] = time.sleep,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    client: UpstoxHistoryClient | None = None,
) -> tuple[tuple[str, Timeframe, date, date, Path, Path, bool], ...]:
    """Fetch and archive monthly chunks; existing exact requests are resumed."""
    if not access_token.strip():
        raise ValueError("a fresh Upstox daily token is required")
    if start < INTRADAY_START:
        raise ValueError(
            "Upstox intraday history starts in January 2022; earlier requests are blocked"
        )
    if end < start:
        raise ValueError("end must be on or after start")
    if minimum_request_interval_seconds < 0:
        raise ValueError("request interval must be non-negative")

    history = client or UpstoxHistoryClient(user_agent="Mozilla/5.0")
    output.mkdir(parents=True, exist_ok=True)
    results: list[tuple[str, Timeframe, date, date, Path, Path, bool]] = []
    last_request_at: float | None = None
    chunks = tuple(iter_month_chunks(start, end))
    for timeframe in (Timeframe.M1, Timeframe.M5):
        for symbol, instrument_key in PILOT_INSTRUMENTS.items():
            for chunk_start, chunk_end in chunks:
                bounds = (chunk_start.isoformat(), chunk_end.isoformat())
                existing = find_history_snapshot(
                    output,
                    instrument_key=instrument_key,
                    symbol=symbol,
                    timeframe=timeframe.value,
                    from_date=bounds[0],
                    to_date=bounds[1],
                )
                resumed = existing is not None
                if existing is None:
                    if last_request_at is not None:
                        elapsed = time.monotonic() - last_request_at
                        wait = minimum_request_interval_seconds - elapsed
                        if wait > 0:
                            sleeper(wait)
                    snapshot = history.fetch_snapshot(
                        instrument_key,
                        symbol=symbol,
                        market=MarketId.IN_EQUITY,
                        timeframe=timeframe,
                        from_date=bounds[0],
                        to_date=bounds[1],
                        ingest_ts=clock().astimezone(UTC),
                        access_token=access_token,
                    )
                    last_request_at = time.monotonic()
                    raw_path, manifest_path = save_history_snapshot(snapshot, output)
                else:
                    raw_path, manifest_path = existing
                results.append(
                    (
                        symbol,
                        timeframe,
                        chunk_start,
                        chunk_end,
                        raw_path,
                        manifest_path,
                        resumed,
                    )
                )
    return tuple(results)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=date.fromisoformat, default=INTRADAY_START)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/p1/raw_intraday"))
    args = parser.parse_args()
    token = getpass.getpass("Fresh Upstox access token (not saved): ")
    rows = collect_pilot_intraday(
        access_token=token,
        start=args.start,
        end=args.end,
        output=args.output,
    )
    fetched = sum(not row[-1] for row in rows)
    resumed = sum(row[-1] for row in rows)
    print(f"requests fetched: {fetched}; exact requests resumed: {resumed}")


if __name__ == "__main__":
    main()
