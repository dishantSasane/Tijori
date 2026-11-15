"""Collect dated raw daily Upstox snapshots for the bounded P1 pilot."""

from __future__ import annotations

import argparse
import getpass
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from trading.adapters.upstox_history import UpstoxHistoryClient
from trading.core.enums import MarketId, Timeframe
from trading.storage.history_archive import save_history_snapshot

PILOT_INSTRUMENTS = {
    "RELIANCE": "NSE_EQ|INE002A01018",
    "INFY": "NSE_EQ|INE009A01021",
    "TCS": "NSE_EQ|INE467B01029",
    "HDFCBANK": "NSE_EQ|INE040A01034",
    "ICICIBANK": "NSE_EQ|INE090A01021",
}


def collect_pilot_daily(
    *,
    access_token: str,
    start: str,
    end: str,
    output: Path,
    minimum_request_interval_seconds: float = 1.0,
    sleeper: Callable[[float], None] = time.sleep,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    client: UpstoxHistoryClient | None = None,
) -> list[tuple[str, Path, Path]]:
    if not access_token.strip():
        raise ValueError("a fresh Upstox daily token is required")
    if minimum_request_interval_seconds < 0:
        raise ValueError("request interval must be non-negative")
    history = client or UpstoxHistoryClient(user_agent="Mozilla/5.0")
    saved: list[tuple[str, Path, Path]] = []
    for index, (symbol, instrument_key) in enumerate(PILOT_INSTRUMENTS.items()):
        if index:
            sleeper(minimum_request_interval_seconds)
        snapshot = history.fetch_snapshot(
            instrument_key,
            symbol=symbol,
            market=MarketId.IN_EQUITY,
            timeframe=Timeframe.D1,
            from_date=start,
            to_date=end,
            ingest_ts=clock().astimezone(UTC),
            access_token=access_token,
        )
        raw_path, manifest_path = save_history_snapshot(snapshot, output)
        saved.append((symbol, raw_path, manifest_path))
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2010-01-01")
    parser.add_argument("--end", default="2015-12-31")
    parser.add_argument("--output", type=Path, default=Path("data/p1/raw"))
    args = parser.parse_args()
    token = getpass.getpass("Fresh Upstox access token (not saved): ")
    for symbol, raw_path, manifest_path in collect_pilot_daily(
        access_token=token,
        start=args.start,
        end=args.end,
        output=args.output,
    ):
        print(f"{symbol}: archived {raw_path.name} and {manifest_path.name}")


if __name__ == "__main__":
    main()
