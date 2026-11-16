from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from tests.scanner.conftest import make_daily_candles
from trading.scanner.scanner import run_scan
from trading.scanner.shortlist_store import active_shortlist, apply_scan
from trading.storage.state_db import connect


def test_apply_scan_promotes_then_demotes() -> None:
    conn = connect(":memory:")
    start = date(2026, 1, 1)
    as_of = start + timedelta(days=20)
    up = make_daily_candles("UP", start, [100.0] * 19 + [150.0])

    ideas = run_scan(["UP"], {"UP": up}, as_of)
    apply_scan(conn, ideas, datetime.combine(as_of, datetime.min.time(), tzinfo=UTC), complete=True)
    active = active_shortlist(conn)
    assert [row["symbol"] for row in active] == ["UP"]

    # Next day the same symbol no longer qualifies -> it must be demoted, not deleted.
    next_day = as_of + timedelta(days=1)
    flat_next_day = run_scan(["UP"], {"UP": []}, next_day)
    apply_scan(
        conn,
        flat_next_day,
        datetime.combine(next_day, datetime.min.time(), tzinfo=UTC),
        complete=True,
    )
    assert active_shortlist(conn) == []
    row = conn.execute("SELECT status FROM scanner_shortlist WHERE symbol = 'UP'").fetchone()
    assert row[0] == "removed"


def test_incomplete_scan_cannot_remove_existing_shortlist_entries() -> None:
    conn = connect(":memory:")
    start = date(2026, 1, 1)
    as_of = start + timedelta(days=20)
    ideas = run_scan(["UP"], {"UP": make_daily_candles("UP", start, [100.0] * 19 + [150.0])}, as_of)
    run_ts = datetime.combine(as_of, datetime.min.time(), tzinfo=UTC)
    apply_scan(conn, ideas, run_ts, complete=True)

    with pytest.raises(ValueError, match="incomplete"):
        apply_scan(conn, [], run_ts + timedelta(days=1), complete=False)
    assert [row["symbol"] for row in active_shortlist(conn)] == ["UP"]
