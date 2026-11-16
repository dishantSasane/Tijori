"""End-of-day summary: signals, trades, and risk rejections (BUILD_ORDER.md P3
item 5). Reads the shared SQLite state DB only -- no broker/exchange calls, so
this is safe to run anytime, including in CI, against a fixture DB.

A "day" is a UTC calendar date (`YYYY-MM-DD`), matching how timestamps are
stored everywhere else in this repo (AGENTS.md §6: all timestamps UTC
internally). The report never calls `datetime.now()` itself -- the caller
supplies the date, so this stays a pure function of (db, date) and is
trivially testable / replayable for any past day.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field


@dataclass
class DailyReport:
    date: str
    fills: int
    signals_rejected: int
    rejection_reasons: dict[str, int] = field(default_factory=dict)
    signal_outcomes: dict[str, int] = field(default_factory=dict)  # result -> count

    def to_dict(self) -> dict[str, object]:
        return {
            "date": self.date,
            "fills": self.fills,
            "signals_rejected": self.signals_rejected,
            "rejection_reasons": self.rejection_reasons,
            "signal_outcomes": self.signal_outcomes,
        }

    def to_markdown(self) -> str:
        lines = [
            f"# Daily report — {self.date}",
            "",
            f"- Fills: {self.fills}",
            f"- Signals rejected by risk engine: {self.signals_rejected}",
            "",
            "## Rejection reasons",
        ]
        if self.rejection_reasons:
            lines += [
                f"- {reason}: {count}" for reason, count in sorted(self.rejection_reasons.items())
            ]
        else:
            lines.append("- none")
        lines += ["", "## Signal outcomes"]
        if self.signal_outcomes:
            lines += [
                f"- {result}: {count}" for result, count in sorted(self.signal_outcomes.items())
            ]
        else:
            lines.append("- none")
        return "\n".join(lines) + "\n"


def build_daily_report(conn: sqlite3.Connection, date: str) -> DailyReport:
    """`date` is `YYYY-MM-DD` (UTC). Matches on the date-prefix of each row's
    stored UTC timestamp string.
    """
    fills = conn.execute(
        "SELECT COUNT(*) FROM fills WHERE ts_utc LIKE ?", (f"{date}%",)
    ).fetchone()[0]

    rejection_reasons: dict[str, int] = {}
    signals_rejected = 0
    for (decision_json,) in conn.execute(
        "SELECT decision_json FROM decisions WHERE created_ts LIKE ?", (f"{date}%",)
    ):
        decision = json.loads(decision_json)
        if not decision.get("allowed", True):
            signals_rejected += 1
            for reason in decision.get("reason_codes") or ["unknown"]:
                rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1

    signal_outcomes: dict[str, int] = {}
    for result, _pct_after_costs in conn.execute(
        "SELECT result, pct_after_costs FROM signal_outcomes WHERE closed_ts LIKE ?",
        (f"{date}%",),
    ):
        signal_outcomes[result] = signal_outcomes.get(result, 0) + 1

    return DailyReport(
        date=date,
        fills=fills,
        signals_rejected=signals_rejected,
        rejection_reasons=rejection_reasons,
        signal_outcomes=signal_outcomes,
    )


if __name__ == "__main__":
    import argparse

    from trading.storage.state_db import connect

    parser = argparse.ArgumentParser(description="Generate a daily paper-trading report.")
    parser.add_argument("db_path")
    parser.add_argument("date", help="YYYY-MM-DD, UTC")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_daily_report(connect(args.db_path), args.date)
    print(json.dumps(report.to_dict(), indent=2) if args.json else report.to_markdown())
