import gzip
import json

import pytest

from trading.data.instruments import (
    InstrumentFileError,
    parse_nse_instruments,
    resolve_nse_symbols,
)


def raw_instruments(rows: list[dict[str, str]]) -> bytes:
    return gzip.compress(json.dumps(rows).encode())


def test_parse_filters_nse_equity_and_resolves_symbols() -> None:
    instruments = parse_nse_instruments(
        raw_instruments(
            [
                {
                    "segment": "NSE_EQ",
                    "instrument_type": "EQ",
                    "trading_symbol": "RELIANCE",
                    "instrument_key": "NSE_EQ|INE002A01018",
                    "isin": "INE002A01018",
                    "name": "RELIANCE INDUSTRIES LTD",
                },
                {
                    "segment": "NSE_FO",
                    "instrument_type": "FUT",
                    "trading_symbol": "RELIANCE FUT",
                    "instrument_key": "NSE_FO|1",
                    "isin": "",
                    "name": "ignored",
                },
            ]
        )
    )
    resolved = resolve_nse_symbols(instruments, ["RELIANCE"])
    assert resolved["RELIANCE"].instrument_key == "NSE_EQ|INE002A01018"


def test_resolve_fails_closed_for_missing_symbol() -> None:
    with pytest.raises(InstrumentFileError, match="not found"):
        resolve_nse_symbols((), ["RELIANCE"])
