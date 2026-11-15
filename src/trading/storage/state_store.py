"""SQLite state store: orders, fills, positions, mode, kill-switch, audit log.

docs/specs/PAPER_BROKER_SPEC.md §4. One file, one connection, WAL-friendly
defaults. This is "broker truth" for the paper broker (there is no external
paper API to reconcile against) — restart reconstructs in-memory state from
these tables (I12).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    request_json TEXT NOT NULL,
    created_ts TEXT NOT NULL,
    updated_ts TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fills (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    qty TEXT NOT NULL,
    price TEXT NOT NULL,
    fees TEXT NOT NULL,
    ledger_source TEXT NOT NULL,
    ts_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS positions (
    market TEXT NOT NULL,
    symbol TEXT NOT NULL,
    sleeve TEXT NOT NULL,
    qty TEXT NOT NULL,
    avg_price TEXT NOT NULL,
    opened_ts TEXT NOT NULL,
    stop_price TEXT,
    PRIMARY KEY (market, symbol, sleeve)
);
CREATE TABLE IF NOT EXISTS pending_fills (
    signal_id TEXT PRIMARY KEY,
    request_json TEXT NOT NULL,
    formed_ts TEXT NOT NULL,
    expires_session_id TEXT
);
CREATE TABLE IF NOT EXISTS mode_state (
    scope TEXT PRIMARY KEY,
    mode TEXT NOT NULL,
    changed_by TEXT NOT NULL,
    changed_ts TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS kill_switch_state (
    scope TEXT PRIMARY KEY,
    engaged INTEGER NOT NULL,
    reason TEXT,
    engaged_ts TEXT,
    released_ts TEXT
);
CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    ts_utc TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS signal_outcomes (
    signal_id TEXT PRIMARY KEY,
    result TEXT NOT NULL,
    pct_after_costs TEXT,
    bars_held INTEGER,
    closed_ts TEXT
);
CREATE TABLE IF NOT EXISTS decided_signals (
    signal_id TEXT PRIMARY KEY,
    decision_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS telegram_decisions (
    signal_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    batch_id TEXT,
    message_id TEXT,
    decided_by TEXT,
    decided_ts TEXT
);
"""


def _dumps(obj: Any) -> str:
    def default(o: Any) -> Any:
        if isinstance(o, Decimal):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        raise TypeError(f"not JSON serializable: {o!r}")

    return json.dumps(obj, default=default)


class StateStore:
    """A thin, honest wrapper around one SQLite file. No ORM — the schema above
    *is* the contract (docs/specs/PAPER_BROKER_SPEC.md §4 table).
    """

    def __init__(self, path: Path | str) -> None:
        self._path = str(path)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # -- orders / fills / positions -------------------------------------------------

    def upsert_order(
        self,
        order_id: str,
        status: str,
        request_json: dict[str, Any],
        *,
        created_ts: datetime,
        updated_ts: datetime,
    ) -> None:
        self._conn.execute(
            "INSERT INTO orders (id, status, request_json, created_ts, updated_ts) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET status=excluded.status, updated_ts=excluded.updated_ts",
            (
                order_id,
                status,
                _dumps(request_json),
                created_ts.isoformat(),
                updated_ts.isoformat(),
            ),
        )
        self._conn.commit()

    def record_fill(
        self,
        fill_id: str,
        order_id: str,
        qty: Decimal,
        price: Decimal,
        fees: Decimal,
        ledger_source: str,
        ts: datetime,
    ) -> None:
        self._conn.execute(
            "INSERT INTO fills (id, order_id, qty, price, fees, ledger_source, ts_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (fill_id, order_id, str(qty), str(price), str(fees), ledger_source, ts.isoformat()),
        )
        self._conn.commit()

    def upsert_position(
        self,
        market: str,
        symbol: str,
        sleeve: str,
        qty: Decimal,
        avg_price: Decimal,
        opened_ts: datetime,
        stop_price: Decimal | None,
    ) -> None:
        if qty <= 0:
            self._conn.execute(
                "DELETE FROM positions WHERE market=? AND symbol=? AND sleeve=?",
                (market, symbol, sleeve),
            )
        else:
            self._conn.execute(
                "INSERT INTO positions "
                "(market, symbol, sleeve, qty, avg_price, opened_ts, stop_price) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(market, symbol, sleeve) DO UPDATE SET "
                "qty=excluded.qty, avg_price=excluded.avg_price, stop_price=excluded.stop_price",
                (
                    market,
                    symbol,
                    sleeve,
                    str(qty),
                    str(avg_price),
                    opened_ts.isoformat(),
                    None if stop_price is None else str(stop_price),
                ),
            )
        self._conn.commit()

    def positions(self) -> list[dict[str, Any]]:
        rows = self._conn.execute("SELECT * FROM positions").fetchall()
        cols = [d[0] for d in self._conn.execute("SELECT * FROM positions").description]
        return [dict(zip(cols, row, strict=True)) for row in rows]

    # -- pending fills ---------------------------------------------------------------

    def add_pending_fill(
        self,
        signal_id: str,
        request_json: dict[str, Any],
        formed_ts: datetime,
        expires_session_id: str | None,
    ) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO pending_fills "
            "(signal_id, request_json, formed_ts, expires_session_id) VALUES (?, ?, ?, ?)",
            (signal_id, _dumps(request_json), formed_ts.isoformat(), expires_session_id),
        )
        self._conn.commit()

    def pop_pending_fill(self, signal_id: str) -> None:
        self._conn.execute("DELETE FROM pending_fills WHERE signal_id=?", (signal_id,))
        self._conn.commit()

    def pending_fill_ids(self) -> list[str]:
        rows = self._conn.execute("SELECT signal_id FROM pending_fills").fetchall()
        return [r[0] for r in rows]

    # -- mode / kill switch ------------------------------------------------------------

    def set_mode(self, scope: str, mode: str, *, changed_by: str, ts: datetime) -> None:
        self._conn.execute(
            "INSERT INTO mode_state (scope, mode, changed_by, changed_ts) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(scope) DO UPDATE SET mode=excluded.mode, changed_by=excluded.changed_by, "
            "changed_ts=excluded.changed_ts",
            (scope, mode, changed_by, ts.isoformat()),
        )
        self._conn.commit()

    def get_mode(self, scope: str, default: str) -> str:
        row = self._conn.execute("SELECT mode FROM mode_state WHERE scope=?", (scope,)).fetchone()
        return row[0] if row else default

    def set_kill_switch(
        self, scope: str, *, engaged: bool, reason: str | None, ts: datetime
    ) -> None:
        if engaged:
            self._conn.execute(
                "INSERT INTO kill_switch_state (scope, engaged, reason, engaged_ts, released_ts) "
                "VALUES (?, 1, ?, ?, NULL) "
                "ON CONFLICT(scope) DO UPDATE SET engaged=1, reason=excluded.reason, "
                "engaged_ts=excluded.engaged_ts, released_ts=NULL",
                (scope, reason, ts.isoformat()),
            )
        else:
            self._conn.execute(
                "INSERT INTO kill_switch_state (scope, engaged, reason, engaged_ts, released_ts) "
                "VALUES (?, 0, NULL, NULL, ?) "
                "ON CONFLICT(scope) DO UPDATE SET engaged=0, reason=NULL, "
                "released_ts=excluded.released_ts",
                (scope, ts.isoformat()),
            )
        self._conn.commit()

    def get_kill_switch(self, scope: str) -> bool:
        row = self._conn.execute(
            "SELECT engaged FROM kill_switch_state WHERE scope=?", (scope,)
        ).fetchone()
        return bool(row[0]) if row else False

    # -- audit log (append-only) -------------------------------------------------------

    def write_audit(
        self, *, event_type: str, actor: str, payload: dict[str, Any], ts: datetime
    ) -> None:
        from uuid import uuid4

        self._conn.execute(
            "INSERT INTO audit_log (id, ts_utc, event_type, actor, payload_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (str(uuid4()), ts.isoformat(), event_type, actor, _dumps(payload)),
        )
        self._conn.commit()

    def audit_events(self, event_type: str | None = None) -> list[dict[str, Any]]:
        if event_type is None:
            rows = self._conn.execute("SELECT * FROM audit_log ORDER BY ts_utc").fetchall()
            desc = self._conn.execute("SELECT * FROM audit_log").description
        else:
            rows = self._conn.execute(
                "SELECT * FROM audit_log WHERE event_type=? ORDER BY ts_utc", (event_type,)
            ).fetchall()
            desc = self._conn.execute(
                "SELECT * FROM audit_log WHERE event_type=?", (event_type,)
            ).description
        cols = [d[0] for d in desc]
        out = []
        for row in rows:
            d = dict(zip(cols, row, strict=True))
            d["payload"] = json.loads(d.pop("payload_json"))
            out.append(d)
        return out

    # -- idempotency (check 14 / I7) ----------------------------------------------------

    def has_decision(self, signal_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM decided_signals WHERE signal_id=?", (signal_id,)
        ).fetchone()
        return row is not None

    def record_decision_once(self, signal_id: str, decision_json: dict[str, Any]) -> bool:
        """Atomic check-and-set: True if this call recorded it, False if it already existed."""
        try:
            self._conn.execute(
                "INSERT INTO decided_signals (signal_id, decision_json) VALUES (?, ?)",
                (signal_id, _dumps(decision_json)),
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    # -- outcomes ------------------------------------------------------------------------

    def record_outcome(
        self,
        signal_id: str,
        result: str,
        pct_after_costs: Decimal | None,
        bars_held: int | None,
        closed_ts: datetime | None,
    ) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO signal_outcomes "
            "(signal_id, result, pct_after_costs, bars_held, closed_ts) VALUES (?, ?, ?, ?, ?)",
            (
                signal_id,
                result,
                None if pct_after_costs is None else str(pct_after_costs),
                bars_held,
                None if closed_ts is None else closed_ts.isoformat(),
            ),
        )
        self._conn.commit()

    def get_outcome(self, signal_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM signal_outcomes WHERE signal_id=?", (signal_id,)
        ).fetchone()
        if row is None:
            return None
        cols = [d[0] for d in self._conn.execute("SELECT * FROM signal_outcomes").description]
        return dict(zip(cols, row, strict=True))


def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()
