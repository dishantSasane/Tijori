"""Archive exact Upstox historical responses and auditable request metadata."""

from __future__ import annotations

import json
import os
import tempfile
from hashlib import sha256
from pathlib import Path

from trading.adapters.upstox_history import UpstoxHistorySnapshot

PARSER_VERSION = "1"


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


def save_history_snapshot(snapshot: UpstoxHistorySnapshot, directory: Path) -> tuple[Path, Path]:
    """Idempotently save original response bytes and a checksum-bound manifest."""
    response_hash = sha256(snapshot.raw_response).hexdigest()
    if response_hash != snapshot.response_sha256:
        raise ValueError("historical response checksum mismatch")
    directory.mkdir(parents=True, exist_ok=True)
    stem = f"{snapshot.symbol}-{snapshot.timeframe.value}-{response_hash}"
    raw_path = directory / f"{stem}.json"
    manifest_path = directory / f"{stem}.manifest.json"
    first_candle = min(snapshot.candles, key=lambda candle: candle.ts_open_utc, default=None)
    last_candle = max(snapshot.candles, key=lambda candle: candle.ts_open_utc, default=None)
    manifest = {
        "schema_version": 1,
        "provider": "upstox",
        "parser_version": PARSER_VERSION,
        "instrument_key": snapshot.instrument_key,
        "symbol": snapshot.symbol,
        "market": snapshot.market.value,
        "timeframe": snapshot.timeframe.value,
        "request": {"from_date": snapshot.from_date, "to_date": snapshot.to_date},
        "retrieved_at_utc": snapshot.retrieved_at_utc.isoformat(),
        "response_sha256": response_hash,
        "raw_response": raw_path.name,
        "candle_count": len(snapshot.candles),
        "first_candle_utc": first_candle.ts_open_utc.isoformat() if first_candle else None,
        "last_candle_utc": last_candle.ts_open_utc.isoformat() if last_candle else None,
        "adjustment_basis": "unverified; raw response preserved, not backtest eligible",
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    if raw_path.exists() and raw_path.read_bytes() != snapshot.raw_response:
        raise ValueError("existing historical response archive is corrupt")
    if manifest_path.exists() and manifest_path.read_bytes() != manifest_bytes:
        raise ValueError("existing historical manifest conflicts with this retrieval")
    if not raw_path.exists():
        _atomic_write(raw_path, snapshot.raw_response)
    if not manifest_path.exists():
        _atomic_write(manifest_path, manifest_bytes)
    return raw_path, manifest_path


def find_history_snapshot(
    directory: Path,
    *,
    instrument_key: str,
    symbol: str,
    timeframe: str,
    from_date: str,
    to_date: str,
) -> tuple[Path, Path] | None:
    """Return one verified archived request, or fail on ambiguous revisions."""
    matches: list[tuple[Path, Path]] = []
    for manifest_path in directory.glob("*.manifest.json"):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(manifest, dict):
            continue
        request = manifest.get("request", {})
        if not isinstance(request, dict):
            continue
        if (
            manifest.get("provider") == "upstox"
            and manifest.get("instrument_key") == instrument_key
            and manifest.get("symbol") == symbol
            and manifest.get("timeframe") == timeframe
            and request.get("from_date") == from_date
            and request.get("to_date") == to_date
        ):
            raw_name = manifest.get("raw_response")
            if not isinstance(raw_name, str) or Path(raw_name).name != raw_name:
                raise ValueError("existing history manifest has invalid raw response path")
            raw_path = directory / raw_name
            raw_bytes = raw_path.read_bytes()
            if sha256(raw_bytes).hexdigest() != manifest.get("response_sha256"):
                raise ValueError("existing history response checksum does not match manifest")
            matches.append((raw_path, manifest_path))
    if len(matches) > 1:
        raise ValueError(
            "multiple archived revisions match this request; choose a new output snapshot"
        )
    return matches[0] if matches else None
