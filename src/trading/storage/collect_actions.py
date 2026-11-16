"""Collect the bounded pilot action feed with a freshly supplied runtime credential."""

from __future__ import annotations

import argparse
import getpass
import time
from pathlib import Path

from trading.adapters.upstox_corporate_actions import UpstoxCorporateActionsClient
from trading.storage.action_archive import save_action_snapshot

# Matches existing pilot candle manifests; this is not historical market membership.
PILOT_ISINS = {
    "RELIANCE": "INE002A01018",
    "INFY": "INE009A01021",
    "TCS": "INE467B01029",
    "HDFCBANK": "INE040A01034",
    "ICICIBANK": "INE090A01021",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/p1/corporate_actions"))
    parser.add_argument("--user-agent", default="Mozilla/5.0")
    args = parser.parse_args()
    token = getpass.getpass("Fresh Upstox access token (not saved): ")
    client = UpstoxCorporateActionsClient(user_agent=args.user_agent)
    for index, (symbol, isin) in enumerate(PILOT_ISINS.items()):
        if index:
            time.sleep(1)
        snapshot = client.fetch(isin, access_token=token)
        path = save_action_snapshot(snapshot, args.output)
        print(
            f"{symbol}: {len(snapshot.events)} reported events; saved {path}; coverage unverified"
        )


if __name__ == "__main__":
    main()
