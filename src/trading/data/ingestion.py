"""Reproducible, provenance-preserving historical candle ingestion."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from trading.adapters.upstox_history import UpstoxHistoryClient
from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle
from trading.storage.candles import CandleStore


class IngestionValidationError(ValueError):
    """Raised when a provider response cannot be safely ingested."""


@dataclass(frozen=True)
class UpstoxHistoryRequest:
    """A complete non-secret description of one historical request."""

    instrument_key: str
    symbol: str
    market: MarketId
    timeframe: Timeframe
    to_date: str
    ingest_ts: datetime
    from_date: str | None = None
    access_token: str | None = None

    def __post_init__(self) -> None:
        if self.ingest_ts.tzinfo is None or self.ingest_ts.utcoffset() != timedelta(0):
            raise ValueError("ingest_ts must be UTC")

    def manifest_fields(self) -> dict[str, str | None]:
        """Return request metadata without ever serializing the access token."""
        return {
            "instrument_key": self.instrument_key,
            "symbol": self.symbol,
            "market": self.market.value,
            "timeframe": self.timeframe.value,
            "to_date": self.to_date,
            "from_date": self.from_date,
            "ingest_ts": self.ingest_ts.astimezone(UTC).isoformat(),
        }


@dataclass(frozen=True)
class IngestionResult:
    candle_count: int
    inserted_count: int
    raw_path: Path
    manifest_path: Path
    raw_sha256: str


def ingest_upstox_history(
    request: UpstoxHistoryRequest,
    *,
    client: UpstoxHistoryClient,
    store: CandleStore,
    archive_dir: Path,
) -> IngestionResult:
    """Archive one Upstox response and append its validated candles.

    Provider responses are commonly newest-first, so chronological ordering is
    normalized before storage. Duplicate timestamps are rejected; exact repeat
    deliveries are otherwise idempotent through ``CandleStore.append``.
    """
    raw, candles = client.fetch_with_raw(
        request.instrument_key,
        symbol=request.symbol,
        market=request.market,
        timeframe=request.timeframe,
        to_date=request.to_date,
        from_date=request.from_date,
        ingest_ts=request.ingest_ts,
        access_token=request.access_token,
    )
    _validate_candles(request, candles)
    ordered = sorted(candles, key=lambda candle: candle.ts_open_utc)
    raw_sha256 = hashlib.sha256(raw).hexdigest()
    archive_dir.mkdir(parents=True, exist_ok=True)
    raw_path = archive_dir / f"upstox-{raw_sha256}.json"
    raw_path.write_bytes(raw)
    manifest_path = archive_dir / f"upstox-{raw_sha256}.manifest.json"
    manifest = {
        "provider": "upstox",
        "request": request.manifest_fields(),
        "raw_sha256": raw_sha256,
        "raw_file": raw_path.name,
        "candle_count": len(ordered),
        "ordering": "ascending_ts_open_utc",
        "adjustment_status": "unadjusted_provider_values",
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    inserted_count = store.append(ordered)
    return IngestionResult(
        candle_count=len(ordered),
        inserted_count=inserted_count,
        raw_path=raw_path,
        manifest_path=manifest_path,
        raw_sha256=raw_sha256,
    )


def _validate_candles(request: UpstoxHistoryRequest, candles: list[Candle]) -> None:
    seen: set[datetime] = set()
    for candle in candles:
        if (
            candle.market is not request.market
            or candle.symbol != request.symbol
            or candle.timeframe is not request.timeframe
        ):
            raise IngestionValidationError("provider candle identity does not match request")
        if candle.ts_open_utc in seen:
            raise IngestionValidationError("provider response contains duplicate candle timestamps")
        seen.add(candle.ts_open_utc)
