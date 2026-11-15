"""Shortlist persistence (P4): list-membership, not strategy-version promotion.

Schema is `scanner_shortlist` in storage/state_db.py. "Promotion" here means
"this symbol is on the shortlist today"; it has nothing to do with the
strategy-version promotion pipeline in docs/STRATEGIES.md §6/§8.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from datetime import datetime

from trading.scanner.models import ScannerIdea


def apply_scan(conn: sqlite3.Connection, ideas: Sequence[ScannerIdea], run_ts: datetime) -> None:
    """Promote every idea onto the shortlist and demote everything else active.

    One call = one day's scanner run. Symbols in ``ideas`` are inserted or
    refreshed as 'active'; symbols currently 'active' but absent from
    ``ideas`` are demoted to 'removed'. This is the only write path for the
    table, so shortlist history always reflects actual scan outcomes.
    """
    run_ts_iso = run_ts.isoformat()
    seen = {(idea.symbol, idea.market.value) for idea in ideas}
    for idea in ideas:
        conn.execute(
            """
            INSERT INTO scanner_shortlist
                (symbol, market, status, first_added_ts, last_seen_ts, removed_ts,
                 target_price, reconsider_price, rank_score, reasons_json)
            VALUES (?, ?, 'active', ?, ?, NULL, ?, ?, ?, ?)
            ON CONFLICT (symbol, market) DO UPDATE SET
                status = 'active',
                last_seen_ts = excluded.last_seen_ts,
                removed_ts = NULL,
                target_price = excluded.target_price,
                reconsider_price = excluded.reconsider_price,
                rank_score = excluded.rank_score,
                reasons_json = excluded.reasons_json
            """,
            (
                idea.symbol,
                idea.market.value,
                run_ts_iso,
                run_ts_iso,
                str(idea.target_price),
                str(idea.reconsider_price),
                str(idea.rank_score),
                json.dumps(list(idea.reasons)),
            ),
        )
    active_rows = conn.execute(
        "SELECT symbol, market FROM scanner_shortlist WHERE status = 'active'"
    ).fetchall()
    for symbol, market in active_rows:
        if (symbol, market) not in seen:
            conn.execute(
                "UPDATE scanner_shortlist SET status = 'removed', removed_ts = ? "
                "WHERE symbol = ? AND market = ?",
                (run_ts_iso, symbol, market),
            )
    conn.commit()


def active_shortlist(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Currently active shortlist entries, best rank first."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM scanner_shortlist WHERE status = 'active' "
        "ORDER BY CAST(rank_score AS REAL) DESC"
    ).fetchall()
    return list(rows)
