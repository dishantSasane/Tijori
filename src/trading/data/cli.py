"""Command-line entry points for P1 collection and scorecard reports."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from trading.backtest.fills import BacktestProfile
from trading.backtest.report import write_phase1_report
from trading.core.enums import MarketId, Timeframe
from trading.data.ingestion import collect_upstox_history, load_upstox_requests
from trading.storage.candles import CandleStore


def main() -> None:
    parser = argparse.ArgumentParser(description="P1 Upstox collection and research reports")
    subparsers = parser.add_subparsers(dest="command", required=True)
    collect = subparsers.add_parser("collect", help="collect Upstox candles from a YAML manifest")
    collect.add_argument("--manifest", type=Path, required=True)
    collect.add_argument("--store", type=Path, required=True)
    collect.add_argument("--archive", type=Path, required=True)
    collect.add_argument("--from-date")
    collect.add_argument("--to-date", required=True)
    collect.add_argument("--ingest-ts", required=True)
    collect.add_argument("--timeframe", choices=[item.value for item in Timeframe], default="1d")
    report = subparsers.add_parser("report", help="run T1/T4 over stored candles")
    report.add_argument("--store", type=Path, required=True)
    report.add_argument("--symbol", required=True)
    report.add_argument("--timeframe", choices=[item.value for item in Timeframe], default="1d")
    report.add_argument("--output", type=Path, required=True)
    report.add_argument("--universe-id", required=True)
    report.add_argument("--data-status", required=True)
    report.add_argument("--quantity", type=Decimal, required=True)
    report.add_argument("--brokerage", type=Decimal, default=Decimal("0"))
    report.add_argument("--slippage-bps", type=Decimal, default=Decimal("0"))
    args = parser.parse_args()
    if args.command == "collect":
        _collect(args)
    else:
        _report(args)


def _collect(args: argparse.Namespace) -> None:
    ingest_ts = _parse_utc(args.ingest_ts)
    timeframe = Timeframe(args.timeframe)
    universe_id, requests = load_upstox_requests(
        args.manifest,
        timeframe=timeframe,
        to_date=args.to_date,
        from_date=args.from_date,
        ingest_ts=ingest_ts,
        access_token=os.environ.get("UPSTOX_ACCESS_TOKEN"),
    )
    from trading.adapters.upstox_history import UpstoxHistoryClient

    with CandleStore(args.store) as store:
        result = collect_upstox_history(
            universe_id,
            requests,
            client=UpstoxHistoryClient(),
            store=store,
            archive_dir=args.archive,
        )
    print(
        json.dumps(
            {
                "universe_id": result.universe_id,
                "requests": result.requests,
                "candles": result.candles,
                "inserted": result.inserted,
            }
        )
    )


def _report(args: argparse.Namespace) -> None:
    timeframe = Timeframe(args.timeframe)
    with CandleStore(args.store) as store:
        candles = store.query(MarketId.IN_EQUITY, args.symbol, timeframe)
    write_phase1_report(
        candles,
        output=args.output,
        quantity=args.quantity,
        profile=BacktestProfile(
            brokerage=args.brokerage,
            slippage_bps=args.slippage_bps,
        ),
        universe_id=args.universe_id,
        data_status=args.data_status,
    )
    print(args.output)


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a UTC offset")
    return parsed.astimezone(UTC)


if __name__ == "__main__":
    main()
