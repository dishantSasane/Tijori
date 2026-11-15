"""Audit log writer backed by the shared SQLite `audit_log` table. Every
order/risk-decision/mode-change/LLM-call is a row here (AGENTS.md §6,
invariant I11) — nothing in `risk`/`broker`/`alerts` writes `AuditEvent`s
anywhere else.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from trading.core.models import AuditEvent


class AuditLog:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def write(
        self, *, ts_utc: datetime, event_type: str, actor: str, payload: dict[str, Any]
    ) -> AuditEvent:
        event = AuditEvent(ts_utc=ts_utc, event_type=event_type, actor=actor, payload=payload)
        self._conn.execute(
            "INSERT INTO audit_log (id, ts_utc, event_type, actor, payload_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                event.id,
                event.ts_utc.isoformat(),
                event.event_type,
                event.actor,
                json.dumps(payload, default=str),
            ),
        )
        self._conn.commit()
        return event

    def events(self, *, event_type: str | None = None) -> list[sqlite3.Row]:
        self._conn.row_factory = sqlite3.Row
        if event_type is None:
            cur = self._conn.execute("SELECT * FROM audit_log ORDER BY ts_utc")
        else:
            cur = self._conn.execute(
                "SELECT * FROM audit_log WHERE event_type = ? ORDER BY ts_utc", (event_type,)
            )
        return list(cur.fetchall())
