import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from trading.adapters.upstox_history import UpstoxHistoryClient
from trading.storage.full_universe_loader import build_full_universe_snapshot
from trading.storage.upstox_instrument_master import EquityMasterEntry

# 61 strictly increasing synthetic sessions: 60-session lookback + effective_date.
SESSIONS = tuple(date(2024, 1, 1) + timedelta(days=i) for i in range(61))
LOOKBACK = SESSIONS[:60]
EFFECTIVE_DATE = SESSIONS[60]


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


def test_full_universe_snapshot_ranks_real_fetched_turnover() -> None:
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


def test_instrument_missing_lookback_sessions_is_excluded_not_crashed() -> None:
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
        sessions=SESSIONS,
        effective_date=EFFECTIVE_DATE,
        k=1,
        sleeper=lambda _: None,
        clock=lambda: datetime(2024, 3, 1, tzinfo=UTC),
    )

    assert snapshot.selected_isins == ("INE002A01018",)
    excluded_isins = {exclusion.isin for exclusion in snapshot.exclusions}
    assert "INE009A01021" in excluded_isins
