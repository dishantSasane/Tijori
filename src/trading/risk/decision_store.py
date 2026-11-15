"""Idempotency store for check 14 (duplicate signal) — invariant I7.

A single SQLite `INSERT ... WHERE NOT EXISTS` is the atomic check-and-set;
two concurrent calls for the same `signal_id` can both run `check()`, but
only one of them succeeds at recording a decision — the other sees the row
already there and must not record a second one (docs/specs/RISK_ENGINE_SPEC.md
§10's note on atomicity).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

from trading.core.models import RiskDecision


class DecisionStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def has_decision(self, signal_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM decisions WHERE signal_id = ?", (signal_id,)
        ).fetchone()
        return row is not None

    def record_if_absent(self, decision: RiskDecision, *, now: datetime) -> bool:
        """Returns True if this call recorded the decision, False if another
        call already had — the caller must treat False as a duplicate.
        """
        cur = self._conn.execute(
            "INSERT INTO decisions (signal_id, decision_json, created_ts) "
            "SELECT ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM decisions WHERE signal_id = ?)",
            (decision.signal_id, decision.model_dump_json(), now.isoformat(), decision.signal_id),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def get(self, signal_id: str) -> RiskDecision | None:
        row = self._conn.execute(
            "SELECT decision_json FROM decisions WHERE signal_id = ?", (signal_id,)
        ).fetchone()
        if row is None:
            return None
        return RiskDecision.model_validate_json(row[0])
