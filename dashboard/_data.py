"""Shared read-only DB access for every dashboard page.

Deliberate simplification (see docs/decisions.md ADR on the P3 dashboard):
pages read the shared SQLite state DB directly instead of going through the
internal FastAPI API that docs/PAGES.md §3 describes. That API does not
exist yet and nothing in this dashboard writes anything, so there is no
safety gap today -- but §4's rule ("the dashboard never talks to brokers
directly; only the engine/API does") still holds, because this file only
ever runs read-only SELECTs. When the API lands, swap this module's
functions for HTTP calls and the pages above it do not need to change.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from trading.storage.state_db import connect

DEFAULT_DB_PATH = "data/state.db"


def get_connection() -> sqlite3.Connection:
    db_path = os.environ.get("TIJORI_STATE_DB", DEFAULT_DB_PATH)
    if db_path != ":memory:" and not Path(db_path).exists():
        # Fail closed, not with a confusing sqlite error: tell the owner what to set.
        raise FileNotFoundError(
            f"No state DB at {db_path!r}. Set TIJORI_STATE_DB to the engine's "
            "database file, or run the engine once to create it."
        )
    return connect(db_path)
