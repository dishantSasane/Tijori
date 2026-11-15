"""SQLite schema shared by the risk engine, paper broker, and Telegram alert
state machine (docs/specs/PAPER_BROKER_SPEC.md §4,
docs/specs/TELEGRAM_ALERT_SPEC.md §2). One file, one connection, so a restart
reload (§4's restart procedure) reads one consistent source instead of
reconciling several files.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
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
    signal_id TEXT NOT NULL,
    qty TEXT NOT NULL,
    avg_price TEXT NOT NULL,
    opened_ts TEXT NOT NULL,
    stop_price TEXT,
    target_price TEXT,
    entry_ref TEXT NOT NULL,
    approved_risk TEXT NOT NULL,
    ledger_source TEXT NOT NULL,
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
    actor TEXT,
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
    closed_ts TEXT,
    ledger_source TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    signal_id TEXT PRIMARY KEY,
    decision_json TEXT NOT NULL,
    created_ts TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exit_requests (
    exit_id TEXT PRIMARY KEY,
    position_id TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    quantity TEXT NOT NULL,
    applied_ts TEXT NOT NULL
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


def connect(db_path: Path | str) -> sqlite3.Connection:
    """Open (creating if needed) the shared state database with the schema
    above applied. `:memory:` is accepted for tests that don't need a restart.
    """
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn
