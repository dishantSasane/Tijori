from datetime import UTC, date, datetime

import pytest

from trading.adapters.upstox_history import UpstoxHistoryClient
from trading.storage.collect_pilot_intraday import collect_pilot_intraday


def test_intraday_collector_resumes_exact_archived_requests(tmp_path) -> None:
    requests: list[str] = []

    def requester(url: str, _headers: dict[str, str]) -> bytes:
        requests.append(url)
        return b'{"status":"success","data":{"candles":[]}}'

    client = UpstoxHistoryClient(
        requester=requester,
        clock=lambda: datetime(2026, 11, 15, tzinfo=UTC),
    )
    first = collect_pilot_intraday(
        access_token="fixture-only",
        start=date(2022, 1, 1),
        end=date(2022, 1, 31),
        output=tmp_path,
        minimum_request_interval_seconds=0,
        client=client,
    )
    assert len(first) == 10
    assert len(requests) == 10
    assert all(not row[-1] for row in first)

    resumed = collect_pilot_intraday(
        access_token="another-runtime-token",
        start=date(2022, 1, 1),
        end=date(2022, 1, 31),
        output=tmp_path,
        minimum_request_interval_seconds=0,
        client=client,
    )
    assert len(resumed) == 10
    assert len(requests) == 10
    assert all(row[-1] for row in resumed)


def test_intraday_collector_refuses_provider_prehistory(tmp_path) -> None:
    with pytest.raises(ValueError, match="starts in January 2022"):
        collect_pilot_intraday(
            access_token="fixture-only",
            start=date(2021, 12, 31),
            end=date(2022, 1, 1),
            output=tmp_path,
        )


def test_intraday_collector_fails_on_ambiguous_archived_revisions(tmp_path) -> None:
    client = UpstoxHistoryClient(
        requester=lambda _url, _headers: b'{"status":"success","data":{"candles":[]}}',
        clock=lambda: datetime(2026, 11, 15, tzinfo=UTC),
    )
    kwargs = {
        "access_token": "fixture-only",
        "start": date(2022, 1, 1),
        "end": date(2022, 1, 31),
        "output": tmp_path,
        "minimum_request_interval_seconds": 0,
        "client": client,
    }
    collect_pilot_intraday(**kwargs)
    # A second response revision for one exact request makes the resume source
    # ambiguous, so the collector must stop rather than mix versions.
    from trading.storage.history_archive import find_history_snapshot

    first = find_history_snapshot(
        tmp_path,
        instrument_key="NSE_EQ|INE002A01018",
        symbol="RELIANCE",
        timeframe="1m",
        from_date="2022-01-01",
        to_date="2022-01-31",
    )
    assert first is not None
    raw_path, manifest_path = first
    import json
    from hashlib import sha256

    manifest = json.loads(manifest_path.read_text())
    manifest["response_sha256"] = sha256(b"second version").hexdigest()
    other_raw = tmp_path / "second.json"
    other_raw.write_bytes(b"second version")
    manifest["raw_response"] = other_raw.name
    other_manifest = tmp_path / "second.manifest.json"
    other_manifest.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="multiple archived revisions"):
        collect_pilot_intraday(**kwargs)
    assert raw_path.exists()
