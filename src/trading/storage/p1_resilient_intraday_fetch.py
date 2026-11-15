"""Fetch one Upstox intraday chunk tolerant of a malformed candle row.

Codex's `UpstoxHistoryClient.fetch_snapshot` (upstox_history.py) parses
every row into a `Candle` before building its snapshot, so a single
malformed row (observed live: HDFCBANK M1, 2024-06-25 09:15 IST -- `open`
below `low`, a genuine Upstox data-quality defect, not a parsing bug)
raises before the raw response is ever archived, losing that chunk's
evidence and halting a resumable multi-month collection run entirely.

Self-contained on purpose -- it duplicates the small HTTP/parse/save steps
instead of importing `upstox_history.py`'s classes, because that adapter
is Codex's actively-changing file and this P1a module must not depend on
whichever version happens to be checked out. Behavior for a well-formed
response is otherwise identical: fetch once, keep every raw byte exactly
as returned, and build the parsed series from only the rows that pass
validation -- never silently "fixing" (e.g. clamping) a bad row, just
excluding it from the parsed series while the full raw response stays
preserved and auditable, and reporting exactly which rows were excluded.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import cast
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE_URL = "https://api.upstox.com/v3/historical-candle"


class ResilientFetchError(RuntimeError):
    """Raised for a transport/API failure -- never for one malformed row."""


@dataclass(frozen=True)
class ParsedIntradayCandle:
    ts_open_utc: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class ResilientFetchResult:
    symbol: str
    timeframe: str
    instrument_key: str
    from_date: str
    to_date: str
    retrieved_at_utc: datetime
    response_sha256: str
    raw_response: bytes
    candles: tuple[ParsedIntradayCandle, ...]
    skipped_rows: tuple[tuple[object, ...], ...]
    """Rows present in the raw response but excluded from `candles` because
    they failed OHLC validation (e.g. open outside [low, high]) -- never
    dropped silently, always reported back to the caller.
    """


def _request(url: str, access_token: str) -> bytes:
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "tijori-research/1.0",
    }
    with urlopen(Request(url, headers=headers, method="GET"), timeout=30) as response:  # noqa: S310
        return cast(bytes, response.read())


def _parse_row(row: object) -> ParsedIntradayCandle:
    if not isinstance(row, list) or len(row) < 6:
        raise ValueError("row has fewer than six fields")
    open_, high, low, close = (Decimal(str(row[i])) for i in (1, 2, 3, 4))
    if not (low <= open_ <= high and low <= close <= high):
        raise ValueError("open/close outside [low, high]")
    return ParsedIntradayCandle(
        ts_open_utc=datetime.fromisoformat(str(row[0])).astimezone(UTC),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=Decimal(str(row[5])),
    )


def fetch_intraday_chunk_skipping_malformed_rows(
    instrument_key: str,
    *,
    symbol: str,
    timeframe: str,
    from_date: str,
    to_date: str,
    access_token: str,
    ingest_ts: datetime | None = None,
) -> ResilientFetchResult:
    unit = {"1m": "1", "5m": "5"}.get(timeframe)
    if unit is None:
        raise ValueError(f"unsupported intraday timeframe: {timeframe!r} (expected '1m'/'5m')")
    encoded = quote(instrument_key, safe="")
    url = f"{BASE_URL}/{encoded}/minutes/{unit}/{to_date}/{from_date}"
    raw_response = _request(url, access_token)
    payload = json.loads(raw_response.decode("utf-8"))
    if payload.get("status") != "success":
        raise ResilientFetchError(f"Upstox API error: {payload}")
    rows = payload.get("data", {}).get("candles", [])
    if not isinstance(rows, list):
        raise ResilientFetchError("Upstox response data.candles is not a list")

    retrieved_at = ingest_ts or datetime.now(UTC)
    candles: list[ParsedIntradayCandle] = []
    skipped: list[tuple[object, ...]] = []
    for row in rows:
        try:
            candles.append(_parse_row(row))
        except (ValueError, TypeError, InvalidOperation):
            skipped.append(tuple(row) if isinstance(row, list) else (row,))

    return ResilientFetchResult(
        symbol=symbol,
        timeframe=timeframe,
        instrument_key=instrument_key,
        from_date=from_date,
        to_date=to_date,
        retrieved_at_utc=retrieved_at,
        response_sha256=sha256(raw_response).hexdigest(),
        raw_response=raw_response,
        candles=tuple(candles),
        skipped_rows=tuple(skipped),
    )


def _atomic_write(path: Path, payload: bytes) -> None:
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".history-")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def save_resilient_snapshot(result: ResilientFetchResult, directory: Path) -> tuple[Path, Path]:
    """Same archive layout as `history_archive.save_history_snapshot`, plus a
    `skipped_rows` field so a malformed-row exclusion is never invisible.
    """
    directory.mkdir(parents=True, exist_ok=True)
    stem = f"{result.symbol}-{result.timeframe}-{result.response_sha256}"
    raw_path = directory / f"{stem}.json"
    manifest_path = directory / f"{stem}.manifest.json"
    first = min((c.ts_open_utc for c in result.candles), default=None)
    last = max((c.ts_open_utc for c in result.candles), default=None)
    manifest = {
        "schema_version": 1,
        "provider": "upstox",
        "symbol": result.symbol,
        "instrument_key": result.instrument_key,
        "market": "in_equity",
        "timeframe": result.timeframe,
        "parser_version": "p1-resilient-1",
        "request": {"from_date": result.from_date, "to_date": result.to_date},
        "retrieved_at_utc": result.retrieved_at_utc.isoformat(),
        "response_sha256": result.response_sha256,
        "raw_response": raw_path.name,
        "candle_count": len(result.candles),
        "first_candle_utc": first.isoformat() if first else None,
        "last_candle_utc": last.isoformat() if last else None,
        "adjustment_basis": "unverified; raw response preserved, not backtest eligible",
        "skipped_rows": [list(row) for row in result.skipped_rows],
    }
    _atomic_write(raw_path, result.raw_response)
    _atomic_write(manifest_path, json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8"))
    return raw_path, manifest_path
