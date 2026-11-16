import gzip
import json
from hashlib import sha256
from pathlib import Path

import pytest

from trading.storage.upstox_instrument_master import (
    fetch_raw_master,
    parse_nse_equity_master,
    save_raw_master,
)


def _gzip_json(rows: list[dict]) -> bytes:
    return gzip.compress(json.dumps(rows).encode("utf-8"))


def test_filters_to_nse_eq_equity_series_only() -> None:
    raw = _gzip_json(
        [
            {
                "segment": "NSE_EQ",
                "instrument_type": "EQ",
                "isin": "INE002A01018",
                "instrument_key": "NSE_EQ|INE002A01018",
                "trading_symbol": "RELIANCE",
                "name": "Reliance Industries",
            },
            # Same segment, different instrument_type (e.g. ETF) -- excluded.
            {
                "segment": "NSE_EQ",
                "instrument_type": "ETF",
                "isin": "INF000000001",
                "instrument_key": "NSE_EQ|INF000000001",
                "trading_symbol": "NIFTYBEES",
                "name": "Nifty BeES",
            },
            # Different segment entirely (e.g. BSE) -- excluded.
            {
                "segment": "BSE_EQ",
                "instrument_type": "EQ",
                "isin": "INE999B01011",
                "instrument_key": "BSE_EQ|INE999B01011",
                "trading_symbol": "SOMEBSE",
                "name": "Some BSE Company",
            },
        ]
    )
    entries = parse_nse_equity_master(raw)
    assert len(entries) == 1
    assert entries[0].trading_symbol == "RELIANCE"
    assert entries[0].isin == "INE002A01018"


def test_duplicate_instrument_key_fails_closed() -> None:
    row = {
        "segment": "NSE_EQ",
        "instrument_type": "EQ",
        "isin": "INE002A01018",
        "instrument_key": "NSE_EQ|INE002A01018",
        "trading_symbol": "RELIANCE",
        "name": "Reliance Industries",
    }
    raw = _gzip_json([row, dict(row)])
    with pytest.raises(ValueError, match="duplicate instrument_key"):
        parse_nse_equity_master(raw)


def test_equity_row_missing_identity_field_fails_closed() -> None:
    raw = _gzip_json(
        [
            {
                "segment": "NSE_EQ",
                "instrument_type": "EQ",
                "isin": None,
                "instrument_key": "NSE_EQ|INE002A01018",
                "trading_symbol": "RELIANCE",
                "name": "Reliance Industries",
            }
        ]
    )
    with pytest.raises(ValueError, match="missing required field"):
        parse_nse_equity_master(raw)


def test_non_array_payload_fails_closed() -> None:
    raw = gzip.compress(json.dumps({"not": "a list"}).encode("utf-8"))
    with pytest.raises(ValueError, match="not a JSON array"):
        parse_nse_equity_master(raw)


def test_fetch_raw_master_uses_injected_fetcher() -> None:
    calls: list[str] = []

    def fake_fetcher(url: str) -> bytes:
        calls.append(url)
        return b"fake-bytes"

    result = fetch_raw_master(fetcher=fake_fetcher)
    assert result == b"fake-bytes"
    assert calls == ["https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz"]


def test_save_raw_master_persists_exact_bytes_under_real_sha256(tmp_path: Path) -> None:
    raw = _gzip_json([{"fake": "row"}])
    path, checksum = save_raw_master(raw, tmp_path)
    assert checksum == sha256(raw).hexdigest()
    assert path.read_bytes() == raw
    assert path.name == f"complete-master-{checksum}.json.gz"


def test_save_raw_master_is_idempotent_for_identical_bytes(tmp_path: Path) -> None:
    raw = _gzip_json([{"fake": "row"}])
    first_path, first_checksum = save_raw_master(raw, tmp_path)
    second_path, second_checksum = save_raw_master(raw, tmp_path)
    assert first_path == second_path
    assert first_checksum == second_checksum


def test_save_raw_master_fails_closed_on_path_corruption(tmp_path: Path) -> None:
    raw = _gzip_json([{"fake": "row"}])
    path, checksum = save_raw_master(raw, tmp_path)
    path.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="corrupt"):
        save_raw_master(raw, tmp_path)
