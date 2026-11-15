"""Shared read-only DB access for dashboard pages.

Note (P4, docs/decisions.md ADR-0032): this file is a duplicate of
`dashboard/_data.py` on the still-unmerged PR #56 (`claude/p3-live-paper-
dashboard`). PR #56 was not on `main` when P4 started, so the Stocks page
below could not import it. Whoever merges #56 and this PR, in either order,
should keep one copy -- they are byte-for-byte the same file.
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
        raise FileNotFoundError(
            f"No state DB at {db_path!r}. Set TIJORI_STATE_DB to the engine's "
            "database file, or run the engine once to create it."
        )
    return connect(db_path)
