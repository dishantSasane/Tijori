"""Build the local, offline manifest for the archived five-symbol P1 pilot."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path
from typing import cast
from urllib.parse import urldefrag

import yaml
from pydantic import HttpUrl, TypeAdapter

from trading.adapters.upstox_corporate_actions import UpstoxCorporateActionsSnapshot
from trading.core.enums import Timeframe
from trading.storage.action_register import (
    ActionRecord,
    ActionRegister,
    CoverageRecord,
    PilotSymbol,
    action_register_sha256,
)
from trading.storage.candle_snapshot import candle_snapshot_sha256
from trading.storage.collect_pilot_daily import PILOT_INSTRUMENTS
from trading.storage.corporate_actions import classify_corporate_action
from trading.storage.evaluation_manifest import (
    P1EvaluationManifest,
    calendar_snapshot_sha256,
    evaluation_manifest_sha256,
)

DAILY_WINDOW = ("2010-01-01", "2026-11-14")
INTRADAY_WINDOW = ("2022-01-01", "2026-11-14")
_PILOT_ISINS = {
    instrument_key.split("|")[-1]: cast(PilotSymbol, symbol)
    for symbol, instrument_key in PILOT_INSTRUMENTS.items()
}
_HTTP_URL = TypeAdapter(HttpUrl)


def _read_history_manifests(directory: Path, timeframe: Timeframe) -> list[Path]:
    manifests = sorted(directory.glob(f"*-{timeframe.value}-*.manifest.json"))
    expected = 15 if timeframe is Timeframe.D1 else 295
    if len(manifests) != expected:
        raise ValueError(f"expected {expected} {timeframe.value} manifests, found {len(manifests)}")
    return manifests


def _session_dates(manifest_paths: list[Path]) -> dict[str, set[date]]:
    sessions: dict[str, set[date]] = {}
    for manifest_path in manifest_paths:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        raw_name = manifest.get("raw_response")
        expected_hash = manifest.get("response_sha256")
        symbol = manifest.get("symbol")
        timeframe = manifest.get("timeframe")
        if not isinstance(raw_name, str) or Path(raw_name).name != raw_name:
            raise ValueError(f"invalid raw-response path in {manifest_path.name}")
        raw_bytes = (manifest_path.parent / raw_name).read_bytes()
        if sha256(raw_bytes).hexdigest() != expected_hash:
            raise ValueError(f"raw-response checksum mismatch in {manifest_path.name}")
        if not isinstance(symbol, str) or not isinstance(timeframe, str):
            raise ValueError(f"missing identity in {manifest_path.name}")
        series = symbol if timeframe == Timeframe.D1.value else f"{symbol}/{timeframe}"
        candles = json.loads(raw_bytes).get("data", {}).get("candles", [])
        if not isinstance(candles, list):
            raise ValueError(f"invalid candle array in {manifest_path.name}")
        dates = sessions.setdefault(series, set())
        for row in candles:
            if not isinstance(row, list) or not row:
                raise ValueError(f"invalid candle row in {manifest_path.name}")
            dates.add(datetime.fromisoformat(str(row[0])).date())
    return sessions


def _publication_date(details: tuple[tuple[str, str], ...]) -> date | None:
    for label, value in details:
        if label.casefold().strip() != "announcement date":
            continue
        for pattern in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value.strip(), pattern).date()
            except ValueError:
                pass
        raise ValueError(f"unsupported announcement date: {value}")
    return None


def _action_register(
    archive_dir: Path,
    *,
    candle_hashes: dict[str, str],
    reviewed_on: date,
) -> ActionRegister:
    snapshots: list[UpstoxCorporateActionsSnapshot] = []
    for path in sorted(archive_dir.glob("*.json")):
        snapshot = UpstoxCorporateActionsSnapshot.model_validate_json(path.read_bytes())
        if sha256(snapshot.raw_response).hexdigest() != snapshot.response_sha256:
            raise ValueError(f"corporate-action response checksum mismatch: {path.name}")
        if snapshot.isin not in _PILOT_ISINS:
            raise ValueError(f"non-pilot ISIN in corporate-action archive: {snapshot.isin}")
        snapshots.append(snapshot)
    if len(snapshots) != len(PILOT_INSTRUMENTS) or {item.isin for item in snapshots} != set(
        _PILOT_ISINS
    ):
        raise ValueError(
            "corporate-action archive must contain exactly one snapshot per pilot ISIN"
        )

    events: list[ActionRecord] = []
    coverage: list[CoverageRecord] = []
    for snapshot in sorted(snapshots, key=lambda item: item.isin):
        symbol = _PILOT_ISINS[snapshot.isin]
        source_ref = f"{urldefrag(snapshot.source_ref)[0]}#sha256={snapshot.response_sha256}"
        for index, event in enumerate(snapshot.events):
            if event.isin != snapshot.isin:
                raise ValueError("corporate-action event ISIN differs from its response")
            event_key = sha256(
                f"{snapshot.response_sha256}|{index}|{event.name}|{event.effective_date.isoformat()}".encode()
            ).hexdigest()
            events.append(
                ActionRecord(
                    event_id=event_key,
                    isin=snapshot.isin,
                    symbol=symbol,
                    ex_date=event.effective_date,
                    publication_date=_publication_date(event.details),
                    action_type=classify_corporate_action(event.name),
                    original_ratio=event.ratio_text,
                    source_url=_HTTP_URL.validate_python(source_ref),
                    reviewer="Codex",
                    review_date=reviewed_on,
                    price_basis="unknown",
                    volume_basis="unknown",
                )
            )

        for timeframe, bounds, candle_key in (
            (Timeframe.D1, DAILY_WINDOW, Timeframe.D1.value),
            (Timeframe.M1, INTRADAY_WINDOW, Timeframe.M1.value),
            (Timeframe.M5, INTRADAY_WINDOW, Timeframe.M5.value),
        ):
            coverage.append(
                CoverageRecord(
                    symbol=symbol,
                    isin=snapshot.isin,
                    timeframe=timeframe,
                    candle_snapshot_sha256=candle_hashes[candle_key],
                    start=date.fromisoformat(bounds[0]),
                    end=date.fromisoformat(bounds[1]),
                    verified=False,
                    source_url=_HTTP_URL.validate_python(source_ref),
                    reviewer="Codex",
                    review_date=reviewed_on,
                )
            )
    return ActionRegister(
        events=tuple(sorted(events, key=lambda item: item.event_id)),
        coverage=tuple(sorted(coverage, key=lambda item: (item.symbol, item.timeframe.value))),
    )


def freeze_p1a_manifest(
    *,
    candle_archive_dir: Path,
    action_archive_dir: Path,
    action_register_path: Path,
    manifest_path: Path,
    reviewed_on: date,
) -> tuple[ActionRegister, P1EvaluationManifest, str]:
    """Verify archived inputs and write the register plus combined manifest."""
    manifests_by_timeframe = {
        timeframe: _read_history_manifests(candle_archive_dir, timeframe)
        for timeframe in (Timeframe.D1, Timeframe.M1, Timeframe.M5)
    }
    windows = {
        Timeframe.D1.value: DAILY_WINDOW,
        Timeframe.M1.value: INTRADAY_WINDOW,
        Timeframe.M5.value: INTRADAY_WINDOW,
    }
    candle_hashes = {
        timeframe.value: candle_snapshot_sha256(
            paths,
            timeframe=timeframe,
            start=windows[timeframe.value][0],
            end=windows[timeframe.value][1],
        )
        for timeframe, paths in manifests_by_timeframe.items()
    }
    action_register = _action_register(
        action_archive_dir,
        candle_hashes=candle_hashes,
        reviewed_on=reviewed_on,
    )
    action_hash = action_register_sha256(action_register)
    action_register_path.parent.mkdir(parents=True, exist_ok=True)
    action_register_path.write_text(
        yaml.safe_dump(action_register.model_dump(mode="json"), sort_keys=True),
        encoding="utf-8",
    )

    daily_sessions = _session_dates(manifests_by_timeframe[Timeframe.D1])
    intraday_sessions = _session_dates(
        manifests_by_timeframe[Timeframe.M1] + manifests_by_timeframe[Timeframe.M5]
    )
    daily_common = set.intersection(*daily_sessions.values())
    calendar_hashes = {
        "daily": calendar_snapshot_sha256(daily_sessions),
        "intraday": calendar_snapshot_sha256(intraday_sessions),
    }
    summary = {
        "daily_common_sessions": len(daily_common),
        "intraday_common_sessions": len(set.intersection(*intraday_sessions.values())),
        **{
            f"{symbol}_daily_sessions": len(rows) for symbol, rows in sorted(daily_sessions.items())
        },
        **{
            f"{series.replace('/', '_')}_sessions": len(rows)
            for series, rows in sorted(intraday_sessions.items())
        },
    }
    manifest = P1EvaluationManifest(
        provider="upstox",
        symbols=tuple(cast(PilotSymbol, symbol) for symbol in PILOT_INSTRUMENTS),
        windows={
            timeframe: (date.fromisoformat(bounds[0]), date.fromisoformat(bounds[1]))
            for timeframe, bounds in windows.items()
        },
        candle_snapshot_sha256=candle_hashes,
        action_register_sha256=action_hash,
        calendar_snapshot_sha256=calendar_hashes,
        calendar_summary=summary,
        action_coverage_status="unverified",
        adjustment_basis={
            "daily_price": "provider-adjusted empirically for split/bonus price continuity",
            "daily_volume": "unverified",
            "intraday_price_volume": "not independently verified",
        },
        transform_version="upstox-v3-provider-adjustment-evidence-v1",
        cost_model_version="BacktestProfile-implementation-v1; profile values are per-run inputs",
    )
    manifest_sha256 = evaluation_manifest_sha256(manifest)
    envelope = {
        "manifest": manifest.model_dump(mode="json"),
        "evaluation_manifest_sha256": manifest_sha256,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return action_register, manifest, manifest_sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candle-archive", type=Path, default=Path("data/p1/raw"))
    parser.add_argument("--action-archive", type=Path, default=Path("data/p1/corporate_actions"))
    parser.add_argument(
        "--action-register",
        type=Path,
        default=Path("data/p1/corporate_actions/pilot-action-register.yaml"),
    )
    parser.add_argument(
        "--manifest", type=Path, default=Path("docs/specs/P1A_EVALUATION_MANIFEST.json")
    )
    parser.add_argument("--reviewed-on", type=date.fromisoformat, required=True)
    args = parser.parse_args()
    register, manifest, digest = freeze_p1a_manifest(
        candle_archive_dir=args.candle_archive,
        action_archive_dir=args.action_archive,
        action_register_path=args.action_register,
        manifest_path=args.manifest,
        reviewed_on=args.reviewed_on,
    )
    print(f"action_register_sha256: {action_register_sha256(register)}")
    print(f"evaluation_manifest_sha256: {digest}")
    print(f"action_coverage_status: {manifest.action_coverage_status}")


if __name__ == "__main__":
    main()
