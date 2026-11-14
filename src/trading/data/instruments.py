"""Upstox instrument-file parsing for reproducible symbol-to-key resolution."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from gzip import decompress
from typing import cast
from urllib.request import Request, urlopen

UPSTOX_NSE_INSTRUMENTS_URL = (
    "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
)


@dataclass(frozen=True)
class UpstoxInstrument:
    trading_symbol: str
    instrument_key: str
    isin: str
    name: str


class InstrumentFileError(ValueError):
    """Raised when an Upstox instrument file is malformed or incomplete."""


def fetch_nse_instruments(
    requester: Callable[[str], bytes] | None = None,
) -> bytes:
    """Fetch the official compressed NSE instrument file without credentials."""
    if requester is not None:
        return requester(UPSTOX_NSE_INSTRUMENTS_URL)
    request = Request(UPSTOX_NSE_INSTRUMENTS_URL, headers={"Accept": "application/gzip"})
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed official URL
        return cast(bytes, response.read())


def parse_nse_instruments(raw_gzip: bytes) -> tuple[UpstoxInstrument, ...]:
    """Parse only normal NSE equity instruments from the official file."""
    try:
        document = json.loads(decompress(raw_gzip).decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InstrumentFileError("invalid Upstox NSE instrument file") from error
    if not isinstance(document, list):
        raise InstrumentFileError("Upstox instrument file must contain a list")
    instruments: list[UpstoxInstrument] = []
    seen_symbols: set[str] = set()
    for row in document:
        if not isinstance(row, dict):
            continue
        if row.get("segment") != "NSE_EQ" or row.get("instrument_type") != "EQ":
            continue
        symbol = row.get("trading_symbol")
        key = row.get("instrument_key")
        isin = row.get("isin")
        name = row.get("name")
        if not all(isinstance(value, str) and value for value in (symbol, key, isin, name)):
            raise InstrumentFileError("NSE equity row is missing required fields")
        assert isinstance(symbol, str)
        assert isinstance(key, str)
        assert isinstance(isin, str)
        assert isinstance(name, str)
        if symbol in seen_symbols:
            raise InstrumentFileError(f"duplicate NSE equity trading symbol: {symbol}")
        seen_symbols.add(symbol)
        instruments.append(
            UpstoxInstrument(
                trading_symbol=symbol,
                instrument_key=key,
                isin=isin,
                name=name,
            )
        )
    return tuple(sorted(instruments, key=lambda item: item.trading_symbol))


def resolve_nse_symbols(
    instruments: Iterable[UpstoxInstrument], symbols: Iterable[str]
) -> dict[str, UpstoxInstrument]:
    """Resolve requested symbols and fail closed if any mapping is absent."""
    by_symbol = {item.trading_symbol: item for item in instruments}
    requested = tuple(dict.fromkeys(symbols))
    missing = sorted(symbol for symbol in requested if symbol not in by_symbol)
    if missing:
        raise InstrumentFileError(f"NSE symbols not found in Upstox file: {', '.join(missing)}")
    return {symbol: by_symbol[symbol] for symbol in requested}
