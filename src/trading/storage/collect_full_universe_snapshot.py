"""CLI: build one real monthly turnover snapshot across the full NSE
cash-equity list via Upstox's own historical-candle API + instrument master.

Requires a fresh Upstox access token (prompted, never saved -- same
convention as `collect_pilot_daily.py`). A full run is ~2,000 instrument
fetches; at the default throttle this takes roughly 5-10 minutes, not
seconds. Run this as its own long-lived process, not inline in a short tool
call.
"""

from __future__ import annotations

import argparse
import getpass
import json
from datetime import date
from pathlib import Path

from trading.adapters.upstox_history import UpstoxHistoryClient
from trading.storage.full_universe_loader import build_full_universe_snapshot
from trading.storage.upstox_instrument_master import fetch_raw_master, parse_nse_equity_master


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sessions-json",
        type=Path,
        required=True,
        help="path to a JSON array of ISO session dates, verified exchange calendar, "
        ">=60 entries before --effective-date",
    )
    parser.add_argument(
        "--effective-date", required=True, help="YYYY-MM-DD, first session of month"
    )
    parser.add_argument("--k", type=int, default=50)
    parser.add_argument("--output", type=Path, default=Path("data/p1/full_universe_snapshot.json"))
    args = parser.parse_args()

    sessions = tuple(
        date.fromisoformat(value) for value in json.loads(args.sessions_json.read_text())
    )
    effective_date = date.fromisoformat(args.effective_date)

    token = getpass.getpass("Fresh Upstox access token (not saved): ")
    print("Fetching Upstox instrument master...")
    master_entries = parse_nse_equity_master(fetch_raw_master())
    print(f"{len(master_entries)} NSE cash-equity instruments found. Fetching daily history...")

    def report(done: int, total: int, symbol: str) -> None:
        if done % 50 == 0 or done == total:
            print(f"  {done}/{total} ({symbol})")

    snapshot = build_full_universe_snapshot(
        client=UpstoxHistoryClient(user_agent="tijori-research/1.0"),
        access_token=token,
        master_entries=master_entries,
        sessions=sessions,
        effective_date=effective_date,
        k=args.k,
        on_progress=report,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(snapshot.model_dump_json(indent=2))
    print(f"Wrote {args.output} -- {len(snapshot.selected_isins)} selected ISINs.")


if __name__ == "__main__":
    main()
