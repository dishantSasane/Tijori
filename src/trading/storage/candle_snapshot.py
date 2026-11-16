"""Deterministic identity for exact archived Upstox candle responses."""

from __future__ import annotations

import json
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

from trading.core.enums import Timeframe


def candle_snapshot_sha256(
    manifest_paths: list[Path], *, timeframe: Timeframe, start: str, end: str
) -> str:
    """Hash a sorted bundle of response manifests after verifying raw bytes.

    This identifies the acquired candle inputs only. Calendar, corporate-action
    register, transforms, and costs belong in the larger evaluation manifest.
    """
    if not manifest_paths:
        raise ValueError("at least one candle response manifest is required")
    if end < start:
        raise ValueError("snapshot end precedes start")
    try:
        date.fromisoformat(start)
        date.fromisoformat(end)
    except ValueError as error:
        raise ValueError("snapshot bounds must be ISO dates") from error

    records: list[dict[str, Any]] = []
    unique_requests: set[tuple[str, str, str, str]] = set()
    for manifest_path in manifest_paths:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or manifest.get("provider") != "upstox":
            raise ValueError("candle manifest must identify Upstox")
        if manifest.get("timeframe") != timeframe.value:
            raise ValueError("candle manifest timeframe differs from requested snapshot")
        request = manifest.get("request")
        if not isinstance(request, dict):
            raise ValueError("candle manifest has no request range")
        from_date, to_date = request.get("from_date"), request.get("to_date")
        if not isinstance(from_date, str) or not isinstance(to_date, str):
            raise ValueError("candle manifest has invalid request dates")
        if from_date > to_date or to_date < start or from_date > end:
            continue
        raw_name = manifest.get("raw_response")
        expected_hash = manifest.get("response_sha256")
        if not isinstance(raw_name, str) or Path(raw_name).name != raw_name:
            raise ValueError("candle manifest raw response path is invalid")
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            raise ValueError("candle manifest response hash is invalid")
        raw_bytes = (manifest_path.parent / raw_name).read_bytes()
        actual_hash = sha256(raw_bytes).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError("candle response checksum does not match its manifest")
        symbol = manifest.get("symbol")
        instrument_key = manifest.get("instrument_key")
        parser_version = manifest.get("parser_version")
        if not isinstance(symbol, str) or not symbol:
            raise ValueError("candle manifest lacks symbol identity")
        if not isinstance(instrument_key, str) or not instrument_key:
            raise ValueError("candle manifest lacks instrument identity")
        if not isinstance(parser_version, str) or not parser_version:
            raise ValueError("candle manifest lacks parser identity")
        identity = (symbol, instrument_key, from_date, to_date)
        if identity in unique_requests:
            raise ValueError("duplicate candle request identity in snapshot")
        unique_requests.add(identity)
        records.append(
            {
                "symbol": symbol,
                "instrument_key": instrument_key,
                "request": {"from_date": from_date, "to_date": to_date},
                "parser_version": parser_version,
                "response_sha256": actual_hash,
            }
        )

    if not records:
        raise ValueError("no candle manifests overlap the requested snapshot window")
    payload = {
        "schema_version": 1,
        "provider": "upstox",
        "timeframe": timeframe.value,
        "window": {"start": start, "end": end},
        "responses": sorted(records, key=lambda row: (row["symbol"], row["request"]["from_date"])),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(canonical).hexdigest()
