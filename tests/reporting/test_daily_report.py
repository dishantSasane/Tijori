from __future__ import annotations

import json

from trading.reporting.daily_report import build_daily_report
from trading.storage.state_db import connect


def _seed(conn):
    conn.execute(
        "INSERT INTO fills VALUES ('f1','o1','10','100','1','paper','2026-11-16T10:00:00+00:00')"
    )
    conn.execute(
        "INSERT INTO fills VALUES ('f2','o2','5','50','1','paper','2026-11-17T10:00:00+00:00')"
    )
    allowed = json.dumps({"allowed": True, "reason_codes": ["ok"]})
    rejected = json.dumps({"allowed": False, "reason_codes": ["kill_switch_engaged"]})
    conn.execute("INSERT INTO decisions VALUES ('s1', ?, '2026-11-16T09:00:00+00:00')", (allowed,))
    conn.execute("INSERT INTO decisions VALUES ('s2', ?, '2026-11-16T09:05:00+00:00')", (rejected,))
    conn.execute(
        "INSERT INTO signal_outcomes VALUES"
        " ('s1','win','2.5',3,'2026-11-16T15:00:00+00:00','paper')"
    )
    conn.commit()


def test_daily_report_scopes_to_the_given_date_and_sums_correctly():
    conn = connect(":memory:")
    _seed(conn)

    report = build_daily_report(conn, "2026-11-16")

    assert report.fills == 1  # the 11-17 fill is excluded
    assert report.signals_rejected == 1
    assert report.rejection_reasons == {"kill_switch_engaged": 1}
    assert report.signal_outcomes == {"win": 1}
    assert str(report.realized_pnl) == "2.5"
    assert "kill_switch_engaged" in report.to_markdown()


def test_empty_day_reports_zeros_not_errors():
    conn = connect(":memory:")
    report = build_daily_report(conn, "2099-01-01")
    assert report.fills == 0
    assert report.signals_rejected == 0
    assert "none" in report.to_markdown()
