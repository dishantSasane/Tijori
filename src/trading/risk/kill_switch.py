"""KillSwitch: persisted engage/release, read fresh every check (invariant I6).

Engagement and release are both explicit, separately-audited calls
(docs/specs/RISK_ENGINE_SPEC.md §8, invariant I10) — nothing here flips
`engaged` as a side effect of time passing, a restart, or a mode change.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

from trading.risk.audit import AuditLog

KillScope = str  # "global" | "sleeve:<name>" | "instance:<strategy_id>:<market>"


class KillSwitch:
    def __init__(self, conn: sqlite3.Connection, audit: AuditLog) -> None:
        self._conn = conn
        self._audit = audit

    def engage(self, scope: KillScope, reason: str, *, actor: str, now: datetime) -> None:
        self._conn.execute(
            """
            INSERT INTO kill_switch_state (scope, engaged, reason, actor, engaged_ts, released_ts)
            VALUES (?, 1, ?, ?, ?, NULL)
            ON CONFLICT(scope) DO UPDATE SET
                engaged=1, reason=excluded.reason, actor=excluded.actor,
                engaged_ts=excluded.engaged_ts, released_ts=NULL
            """,
            (scope, reason, actor, now.isoformat()),
        )
        self._conn.commit()
        self._audit.write(
            ts_utc=now,
            event_type="kill_switch_engaged",
            actor=actor,
            payload={"scope": scope, "reason": reason},
        )

    def release(self, scope: KillScope, *, actor: str, now: datetime) -> None:
        self._conn.execute(
            "UPDATE kill_switch_state SET engaged=0, released_ts=? WHERE scope=?",
            (now.isoformat(), scope),
        )
        self._conn.commit()
        self._audit.write(
            ts_utc=now, event_type="kill_switch_released", actor=actor, payload={"scope": scope}
        )

    def is_engaged(self, scope: KillScope) -> bool:
        row = self._conn.execute(
            "SELECT engaged FROM kill_switch_state WHERE scope = ?", (scope,)
        ).fetchone()
        return bool(row and row[0])

    def engaged_scopes(self) -> list[KillScope]:
        rows = self._conn.execute(
            "SELECT scope FROM kill_switch_state WHERE engaged = 1"
        ).fetchall()
        return [r[0] for r in rows]


def scopes_to_check(*, market: str, sleeve: str, strategy_id: str) -> list[KillScope]:
    """Check order per RISK_ENGINE_SPEC.md §2 check 1: global, then sleeve, then instance."""
    return ["global", f"sleeve:{sleeve}", f"instance:{strategy_id}:{market}"]
