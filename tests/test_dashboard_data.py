"""The one runnable check for dashboard/_data.py: it fails closed (a clear
error, not a raw sqlite traceback) when the state DB is missing, and
succeeds for the in-memory sentinel used by other tests.
"""

from __future__ import annotations

import os

import pytest

from dashboard._data import get_connection


def test_missing_db_raises_a_clear_error(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("TIJORI_STATE_DB", str(tmp_path / "does-not-exist.db"))
    with pytest.raises(FileNotFoundError, match="TIJORI_STATE_DB"):
        get_connection()


def test_memory_sentinel_works(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIJORI_STATE_DB", ":memory:")
    conn = get_connection()
    assert conn.execute("SELECT 1").fetchone() == (1,)
    os.environ.pop("TIJORI_STATE_DB", None)
