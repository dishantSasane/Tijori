import gzip
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from trading.adapters.upstox_history import UpstoxHistoryClient
from trading.storage.full_universe_loader import (
    DEFAULT_MINIMUM_REQUEST_INTERVAL_SECONDS,
    build_full_universe_snapshot,
    fetch_turnover_observations_for_instrument,
)
from trading.storage.upstox_instrument_master import EquityMasterEntry

# 61 strictly increasing synthetic sessions: 60-session lookback + effective_date.
SESSIONS = tuple(date(2024, 1, 1) + timedelta(days=i) for i in range(61))
LOOKBACK = SESSIONS[:60]
EFFECTIVE_DATE = SESSIONS[60]
FAKE_MASTER_BYTES = gzip.compress(b"[]")


def _candle_row(day: date, close: str, volume: str) -> list[object]:
    return [
        datetime(day.year, day.month, day.day, tzinfo=UTC).isoformat(),
        close,
        close,
        close,
        close,
        volume,
    ]


def _upstox_success_body(rows: list[list[object]]) -> bytes:
    return json.dumps({"status": "success", "data": {"candles": rows}}).encode("utf-8")


def test_minimum_request_interval_stays_under_the_2000_per_30_minute_budget() -> None:
    """Upstox's real binding budget is 2,000 requests per 30 minutes (900
    seconds), not 500/minute -- 500/min alone would allow a burst that
    blows the 30-minute window. This is the exact regression for the
    blocker: the previous default (0.15s) implied ~400 req/min / ~12,000
    per 30 minutes, six times over budget.
    """
    requests_in_thirty_minutes = 1800 / DEFAULT_MINIMUM_REQUEST_INTERVAL_SECONDS
    assert requests_in_thirty_minutes <= 2000
    requests_in_one_minute = 60 / DEFAULT_MINIMUM_REQUEST_INTERVAL_SECONDS
    assert requests_in_one_minute <= 500


def test_full_universe_snapshot_ranks_real_fetched_turnover(tmp_path: Path) -> None:
    entries = [
        EquityMasterEntry(
            instrument_key="NSE_EQ|INE002A01018",
            isin="INE002A01018",
            trading_symbol="RELIANCE",
            name="Reliance Industries",
        ),
        EquityMasterEntry(
            instrument_key="NSE_EQ|INE009A01021",
            isin="INE009A01021",
            trading_symbol="INFY",
            name="Infosys",
        ),
    ]

    # RELIANCE: close=100, volume=1000 every day -> turnover 100,000/day.
    # INFY: close=10, volume=100 every day -> turnover 1,000/day. RELIANCE ranks first.
    responses_by_instrument = {
        "NSE_EQ|INE002A01018": _upstox_success_body(
            [_candle_row(day, "100", "1000") for day in LOOKBACK]
        ),
        "NSE_EQ|INE009A01021": _upstox_success_body(
            [_candle_row(day, "10", "100") for day in LOOKBACK]
        ),
    }

    def fake_requester(path: str, headers: dict[str, str]) -> bytes:
        for key, body in responses_by_instrument.items():
            if key.replace("|", "%7C") in path or key in path:
                return body
        raise AssertionError(f"unexpected request path: {path}")

    client = UpstoxHistoryClient(requester=fake_requester)
    sleeps: list[float] = []

    snapshot = build_full_universe_snapshot(
        client=client,
        access_token="fake-token",
        master_entries=entries,
        master_raw_bytes=FAKE_MASTER_BYTES,
        archive_directory=tmp_path,
        sessions=SESSIONS,
        effective_date=EFFECTIVE_DATE,
        k=1,
        sleeper=sleeps.append,
        clock=lambda: datetime(2024, 3, 1, tzinfo=UTC),
    )

    assert snapshot.selected_isins == ("INE002A01018",)
    assert snapshot.ranked_candidates[0].isin == "INE002A01018"
    assert snapshot.ranked_candidates[0].median_turnover_inr == Decimal("100000")
    assert snapshot.ranked_candidates[1].isin == "INE009A01021"
    assert snapshot.ranked_candidates[1].median_turnover_inr == Decimal("1000")
    # One sleep between the two instrument fetches, none before the first.
    assert len(sleeps) == 1


def test_snapshot_evidence_is_persisted_and_hashed_for_reproducibility(tmp_path: Path) -> None:
    """Every monthly snapshot must be independently reproducible later: the
    exact raw master bytes and every instrument's exact raw candle response
    must be persisted on disk and bound into UniverseProvenance.raw_files
    with real SHA-256 checksums -- not the previous placeholder
    (`checksum="n/a-live-api"`).
    """
    entries = [
        EquityMasterEntry(
            instrument_key="NSE_EQ|INE002A01018",
            isin="INE002A01018",
            trading_symbol="RELIANCE",
            name="Reliance Industries",
        ),
    ]
    body = _upstox_success_body([_candle_row(day, "100", "1000") for day in LOOKBACK])

    def fake_requester(path: str, headers: dict[str, str]) -> bytes:
        return body

    client = UpstoxHistoryClient(requester=fake_requester)
    snapshot = build_full_universe_snapshot(
        client=client,
        access_token="fake-token",
        master_entries=entries,
        master_raw_bytes=FAKE_MASTER_BYTES,
        archive_directory=tmp_path,
        sessions=SESSIONS,
        effective_date=EFFECTIVE_DATE,
        k=1,
        sleeper=lambda _: None,
        clock=lambda: datetime(2024, 3, 1, tzinfo=UTC),
    )

    # One raw_files entry for the master, one for the single instrument.
    assert len(snapshot.raw_files) == 2
    checksums = {entry.checksum for entry in snapshot.raw_files}
    assert all(checksum != "n/a-live-api" for checksum in checksums)
    assert all(len(checksum) == 64 for checksum in checksums)

    # The exact master bytes were actually written to disk under that hash.
    master_files = list(tmp_path.glob("complete-master-*.json.gz"))
    assert len(master_files) == 1
    assert master_files[0].read_bytes() == FAKE_MASTER_BYTES

    # The exact candle response was actually written to disk too.
    candle_files = [
        path
        for path in tmp_path.glob("RELIANCE-*.json")
        if not path.name.endswith(".manifest.json")
    ]
    assert len(candle_files) == 1
    assert candle_files[0].read_bytes() == body


def test_instrument_missing_lookback_sessions_is_excluded_not_crashed(tmp_path: Path) -> None:
    entries = [
        EquityMasterEntry(
            instrument_key="NSE_EQ|INE002A01018",
            isin="INE002A01018",
            trading_symbol="RELIANCE",
            name="Reliance Industries",
        ),
        EquityMasterEntry(
            instrument_key="NSE_EQ|INE009A01021",
            isin="INE009A01021",
            trading_symbol="INFY",
            name="Infosys",
        ),
    ]
    # INFY only has candles for the last 10 lookback sessions (recently listed).
    responses_by_instrument = {
        "NSE_EQ|INE002A01018": _upstox_success_body(
            [_candle_row(day, "100", "1000") for day in LOOKBACK]
        ),
        "NSE_EQ|INE009A01021": _upstox_success_body(
            [_candle_row(day, "10", "100") for day in LOOKBACK[-10:]]
        ),
    }

    def fake_requester(path: str, headers: dict[str, str]) -> bytes:
        for key, body in responses_by_instrument.items():
            if key.replace("|", "%7C") in path or key in path:
                return body
        raise AssertionError(f"unexpected request path: {path}")

    client = UpstoxHistoryClient(requester=fake_requester)
    snapshot = build_full_universe_snapshot(
        client=client,
        access_token="fake-token",
        master_entries=entries,
        master_raw_bytes=FAKE_MASTER_BYTES,
        archive_directory=tmp_path,
        sessions=SESSIONS,
        effective_date=EFFECTIVE_DATE,
        k=1,
        sleeper=lambda _: None,
        clock=lambda: datetime(2024, 3, 1, tzinfo=UTC),
    )

    assert snapshot.selected_isins == ("INE002A01018",)
    excluded_isins = {exclusion.isin for exclusion in snapshot.exclusions}
    assert "INE009A01021" in excluded_isins


def test_isolated_single_session_gap_decoded_as_confirmed_no_trade_day(tmp_path: Path) -> None:
    """Upstox omits the row entirely for an illiquid instrument's no-trade
    day rather than returning an explicit zero-volume candle (confirmed
    empirically against live data: SONAL/INE321M01017 has no row for
    2026-08-12, an ordinary trading day). A single missing session with
    real candles on both immediate neighbors must be decoded as a
    confirmed zero-turnover observation, not fail the whole snapshot.
    """
    entry = EquityMasterEntry(
        instrument_key="NSE_EQ|INE321M01017",
        isin="INE321M01017",
        trading_symbol="SONAL",
        name="Sonal Mercantile",
    )
    gap_session = LOOKBACK[30]
    rows = [_candle_row(day, "90", "100") for day in LOOKBACK if day != gap_session]

    def fake_requester(path: str, headers: dict[str, str]) -> bytes:
        return _upstox_success_body(rows)

    client = UpstoxHistoryClient(requester=fake_requester)
    instrument, observations, decoded, response_sha256 = fetch_turnover_observations_for_instrument(
        client,
        entry,
        sessions=LOOKBACK,
        access_token="fake-token",
        clock=lambda: datetime(2024, 3, 1, tzinfo=UTC),
        archive_directory=tmp_path,
    )

    assert decoded == (gap_session,)
    assert response_sha256 is not None
    by_date = {observation.session_date: observation for observation in observations}
    assert len(observations) == len(LOOKBACK)
    assert by_date[gap_session].turnover_inr == Decimal(0)
    assert by_date[gap_session].explicit_zero is True


def test_response_sha256_is_none_when_no_archive_directory_supplied() -> None:
    entry = EquityMasterEntry(
        instrument_key="NSE_EQ|INE321M01017",
        isin="INE321M01017",
        trading_symbol="SONAL",
        name="Sonal Mercantile",
    )
    rows = [_candle_row(day, "90", "100") for day in LOOKBACK]

    def fake_requester(path: str, headers: dict[str, str]) -> bytes:
        return _upstox_success_body(rows)

    client = UpstoxHistoryClient(requester=fake_requester)
    _, _, _, response_sha256 = fetch_turnover_observations_for_instrument(
        client,
        entry,
        sessions=LOOKBACK,
        access_token="fake-token",
        clock=lambda: datetime(2024, 3, 1, tzinfo=UTC),
    )
    assert response_sha256 is None


def test_multi_session_gap_is_not_decoded_stays_a_hard_error(tmp_path: Path) -> None:
    """A run of consecutive missing sessions (e.g. a suspension) must not be
    decoded as no-trade days -- it should still surface as missing
    observations, which `build_snapshot` turns into a hard error. This is
    the explicit boundary the user drew: isolated single-day gaps only.
    """
    entry = EquityMasterEntry(
        instrument_key="NSE_EQ|INE321M01017",
        isin="INE321M01017",
        trading_symbol="SONAL",
        name="Sonal Mercantile",
    )
    gap_sessions = set(LOOKBACK[30:33])  # three consecutive missing sessions
    rows = [_candle_row(day, "90", "100") for day in LOOKBACK if day not in gap_sessions]

    def fake_requester(path: str, headers: dict[str, str]) -> bytes:
        return _upstox_success_body(rows)

    client = UpstoxHistoryClient(requester=fake_requester)
    instrument, observations, decoded, _ = fetch_turnover_observations_for_instrument(
        client,
        entry,
        sessions=LOOKBACK,
        access_token="fake-token",
        clock=lambda: datetime(2024, 3, 1, tzinfo=UTC),
        archive_directory=tmp_path,
    )

    assert decoded == ()
    observed_dates = {observation.session_date for observation in observations}
    assert gap_sessions.isdisjoint(observed_dates)
    assert len(observations) == len(LOOKBACK) - len(gap_sessions)


def test_leading_gap_is_not_decoded(tmp_path: Path) -> None:
    """A missing session with no earlier candle at all (e.g. not yet
    listed) must not be decoded as a no-trade day."""
    entry = EquityMasterEntry(
        instrument_key="NSE_EQ|INE321M01017",
        isin="INE321M01017",
        trading_symbol="SONAL",
        name="Sonal Mercantile",
    )
    rows = [_candle_row(day, "90", "100") for day in LOOKBACK[1:]]  # missing the very first day

    def fake_requester(path: str, headers: dict[str, str]) -> bytes:
        return _upstox_success_body(rows)

    client = UpstoxHistoryClient(requester=fake_requester)
    instrument, observations, decoded, _ = fetch_turnover_observations_for_instrument(
        client,
        entry,
        sessions=LOOKBACK,
        access_token="fake-token",
        clock=lambda: datetime(2024, 3, 1, tzinfo=UTC),
        archive_directory=tmp_path,
    )

    assert decoded == ()
    observed_dates = {observation.session_date for observation in observations}
    assert LOOKBACK[0] not in observed_dates


def test_decoded_no_trade_day_callback_fires_on_the_full_run(tmp_path: Path) -> None:
    entries = [
        EquityMasterEntry(
            instrument_key="NSE_EQ|INE321M01017",
            isin="INE321M01017",
            trading_symbol="SONAL",
            name="Sonal Mercantile",
        ),
    ]
    gap_session = LOOKBACK[30]
    rows = [_candle_row(day, "90", "100") for day in LOOKBACK if day != gap_session]

    def fake_requester(path: str, headers: dict[str, str]) -> bytes:
        return _upstox_success_body(rows)

    client = UpstoxHistoryClient(requester=fake_requester)
    fired: list[tuple[str, date]] = []
    build_full_universe_snapshot(
        client=client,
        access_token="fake-token",
        master_entries=entries,
        master_raw_bytes=FAKE_MASTER_BYTES,
        archive_directory=tmp_path,
        sessions=SESSIONS,
        effective_date=EFFECTIVE_DATE,
        k=1,
        sleeper=lambda _: None,
        clock=lambda: datetime(2024, 3, 1, tzinfo=UTC),
        on_decoded_no_trade_day=lambda isin, day: fired.append((isin, day)),
    )
    assert fired == [("INE321M01017", gap_session)]
