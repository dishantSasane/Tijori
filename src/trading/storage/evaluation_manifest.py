"""Canonical identities for frozen P1 candle, calendar and action evidence."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import date
from hashlib import sha256
from typing import Literal

from pydantic import Field, field_validator, model_validator

from trading.core.models import Contract
from trading.storage.action_register import PilotSymbol

_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_PILOT_SYMBOLS = frozenset({"RELIANCE", "INFY", "TCS", "HDFCBANK", "ICICIBANK"})


class P1EvaluationManifest(Contract):
    """Immutable identity of the bounded five-symbol P1 pilot inputs."""

    schema_version: Literal[1] = 1
    provider: Literal["upstox"]
    symbols: tuple[PilotSymbol, ...]
    windows: dict[str, tuple[date, date]]
    candle_snapshot_sha256: dict[str, str]
    action_register_sha256: str = Field(pattern=_SHA256_PATTERN)
    calendar_snapshot_sha256: dict[str, str]
    calendar_summary: dict[str, int]
    action_coverage_status: Literal["verified", "partial", "unverified"]
    adjustment_basis: dict[str, str]
    transform_version: str = Field(min_length=1)
    cost_model_version: str = Field(min_length=1)

    @field_validator("symbols")
    @classmethod
    def sort_symbols(cls, value: tuple[PilotSymbol, ...]) -> tuple[PilotSymbol, ...]:
        if len(set(value)) != len(value):
            raise ValueError("manifest symbols must be unique")
        return tuple(sorted(value))

    @model_validator(mode="after")
    def validate_scope_and_hashes(self) -> P1EvaluationManifest:
        if set(self.symbols) != _PILOT_SYMBOLS:
            raise ValueError("manifest must identify the exact five-symbol P1 pilot")
        if set(self.windows) != {"1d", "1m", "5m"}:
            raise ValueError("manifest windows must cover 1d, 1m, and 5m")
        if set(self.candle_snapshot_sha256) != {"1d", "1m", "5m"}:
            raise ValueError("manifest candle hashes must cover 1d, 1m, and 5m")
        if set(self.calendar_snapshot_sha256) != {"daily", "intraday"}:
            raise ValueError("manifest calendar hashes must cover daily and intraday")
        if self.calendar_summary.get("daily_common_sessions", 0) <= 0:
            raise ValueError("manifest must record the positive daily common-session count")
        if set(self.adjustment_basis) != {"daily_price", "daily_volume", "intraday_price_volume"}:
            raise ValueError("manifest must state each daily/intraday adjustment basis")
        for value in (
            *self.candle_snapshot_sha256.values(),
            *self.calendar_snapshot_sha256.values(),
        ):
            if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
                raise ValueError("manifest hashes must be lowercase SHA-256 digests")
        for timeframe, (start, end) in self.windows.items():
            if end < start:
                raise ValueError(f"manifest {timeframe} window end precedes start")
        return self


def calendar_snapshot_sha256(sessions_by_symbol: Mapping[str, Iterable[date]]) -> str:
    """Hash exact observed session dates, retaining outlier sessions by symbol."""
    if len(sessions_by_symbol) < 2:
        raise ValueError("calendar snapshot requires at least two symbols")
    normalized: dict[str, list[str]] = {}
    session_sets: dict[str, set[date]] = {}
    for symbol, raw_sessions in sessions_by_symbol.items():
        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol or normalized_symbol in normalized:
            raise ValueError("calendar symbols must be non-empty and unique")
        rows = list(raw_sessions)
        if not rows:
            raise ValueError("each calendar symbol must have non-empty sessions")
        if any(not isinstance(session, date) for session in rows):
            raise ValueError("calendar sessions must be dates")
        if len(set(rows)) != len(rows):
            raise ValueError(f"calendar sessions must be unique for {normalized_symbol}")
        session_sets[normalized_symbol] = set(rows)
        normalized[normalized_symbol] = sorted(session.isoformat() for session in rows)

    common = set.intersection(*session_sets.values())
    payload = {
        "schema_version": 1,
        "sessions_by_symbol": {symbol: normalized[symbol] for symbol in sorted(normalized)},
        "common_sessions": sorted(session.isoformat() for session in common),
        "symbol_only_dates": {
            symbol: sorted(session.isoformat() for session in sessions - common)
            for symbol, sessions in sorted(session_sets.items())
        },
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(canonical).hexdigest()


def evaluation_manifest_sha256(manifest: P1EvaluationManifest) -> str:
    """Hash normalized manifest fields; dictionary insertion order is irrelevant."""
    canonical = json.dumps(
        manifest.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256(canonical).hexdigest()
