"""Upstox's official complete instrument master (not NSE's site, not bhavcopy).

Published at https://assets.upstox.com/market-quote/instruments/exchange/
complete.json.gz -- Upstox's own documented BOD-contract list, refreshed
daily, covering every tradable instrument (`instrument_key`, `isin`,
`trading_symbol`, `instrument_type`, `segment`, `name`) across the exchanges
it supports. This sidesteps NSE's own site/bhavcopy ToU question entirely:
it is a licensed API call against the broker Upstox is already the P1 candle
source for (ADR-0023), just at full-universe scope instead of five symbols.

This module only normalizes the already-fetched bytes; it does not establish
rights beyond what ADR-0023 already covers for Upstox itself.
"""

from __future__ import annotations

import gzip
import json
import os
import tempfile
from collections.abc import Callable
from hashlib import sha256
from pathlib import Path
from typing import cast
from urllib.request import Request, urlopen

from pydantic import Field

from trading.core.models import Contract

COMPLETE_MASTER_URL = "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz"

#: Upstox's `segment` value for NSE cash equities.
NSE_EQUITY_SEGMENT = "NSE_EQ"
#: Upstox's `instrument_type` value for an ordinary equity series (not ETF/REIT/etc).
EQUITY_SERIES_INSTRUMENT_TYPE = "EQ"


class EquityMasterEntry(Contract):
    """One NSE cash-equity row from Upstox's instrument master."""

    instrument_key: str = Field(min_length=1)
    isin: str = Field(min_length=12, max_length=12)
    trading_symbol: str = Field(min_length=1)
    name: str = Field(min_length=1)


def _fetch_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "tijori-research/1.0"}, method="GET")
    with urlopen(request, timeout=60) as response:  # noqa: S310 - fixed HTTPS Upstox CDN URL
        return cast(bytes, response.read())


def fetch_raw_master(
    *, fetcher: Callable[[str], bytes] = _fetch_bytes, url: str = COMPLETE_MASTER_URL
) -> bytes:
    """Download the gzipped complete instrument master, unparsed."""
    return fetcher(url)


def _atomic_write(path: Path, payload: bytes) -> None:
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".master-")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def save_raw_master(raw_gzip_json: bytes, directory: Path) -> tuple[Path, str]:
    """Persist the exact fetched master bytes, content-addressed by their
    real SHA-256 -- so a later snapshot can be bound to, and reproduced
    from, the literal bytes it was built against, not just a trusted claim.
    Idempotent: re-saving identical bytes is a no-op; a path collision with
    different bytes (same hash claimed, different content) fails closed.
    """
    checksum = sha256(raw_gzip_json).hexdigest()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"complete-master-{checksum}.json.gz"
    if path.exists() and path.read_bytes() != raw_gzip_json:
        raise ValueError("existing instrument-master archive is corrupt")
    if not path.exists():
        _atomic_write(path, raw_gzip_json)
    return path, checksum


def parse_nse_equity_master(raw_gzip_json: bytes) -> list[EquityMasterEntry]:
    """Decompress and filter Upstox's complete master to NSE cash equities.

    Fails closed on a row this parser cannot classify rather than silently
    including or excluding it: a row in the NSE_EQ segment whose
    `instrument_type` isn't the plain equity series is skipped (not raised),
    since the master legitimately mixes ETFs/REITs/InvITs into the same
    segment and those are out of scope for the cash-equity turnover universe,
    not a parser error.
    """
    rows = json.loads(gzip.decompress(raw_gzip_json))
    if not isinstance(rows, list):
        raise ValueError("instrument master is not a JSON array")
    entries: list[EquityMasterEntry] = []
    seen_keys: set[str] = set()
    for row in rows:
        if row.get("segment") != NSE_EQUITY_SEGMENT:
            continue
        if row.get("instrument_type") != EQUITY_SERIES_INSTRUMENT_TYPE:
            continue
        isin = row.get("isin")
        instrument_key = row.get("instrument_key")
        trading_symbol = row.get("trading_symbol")
        name = row.get("name")
        if not (isin and instrument_key and trading_symbol and name):
            # A row claiming to be an equity series but missing an identity
            # field is a data-quality problem, not a silent skip.
            raise ValueError(f"NSE_EQ equity row missing required field: {row}")
        if instrument_key in seen_keys:
            raise ValueError(f"duplicate instrument_key in master: {instrument_key}")
        seen_keys.add(instrument_key)
        entries.append(
            EquityMasterEntry(
                instrument_key=instrument_key,
                isin=isin,
                trading_symbol=trading_symbol,
                name=name,
            )
        )
    return entries
