"""Reconciliation: PaperBroker's reported state vs. an independently-replayed
reconstruction from `audit_log`. Backs invariant I12
(docs/specs/PAPER_BROKER_SPEC.md §4): "on restart, in-memory state is
reconstructed from SQLite, and reconstruction must be exact or the engine
halts new entries and alerts." This is that dual-read, as a standalone,
testable check rather than something only implicitly true of the restart path.

`audit_log` is the append-only source of truth (AGENTS.md §6, invariant I11)
-- `positions`/`fills` are the broker's own direct-read tables. If the two
ever disagree, something wrote to one without writing to the other, which is
exactly the class of bug this function exists to catch.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class Mismatch:
    position_key: str
    expected_qty: Decimal | None  # None means "should not exist"
    actual_qty: Decimal | None  # None means "does not exist"

    def __str__(self) -> str:
        return (
            f"{self.position_key}: audit_log says qty={self.expected_qty}, "
            f"positions table says qty={self.actual_qty}"
        )


@dataclass(frozen=True)
class ReconciliationResult:
    ok: bool
    mismatches: tuple[Mismatch, ...] = field(default_factory=tuple)

    def raise_if_inconsistent(self) -> None:
        """Fail-closed entry point (§4): a caller that wants I12's "halt new
        entries and alert" behaviour calls this and catches the exception to
        trigger that halt -- this module only detects, callers decide what
        "halt" means in their own context.
        """
        if not self.ok:
            raise ReconciliationError(
                f"positions table disagrees with audit_log replay on {len(self.mismatches)} "
                f"position(s): {'; '.join(str(m) for m in self.mismatches)}"
            )


class ReconciliationError(RuntimeError):
    """Raised by `ReconciliationResult.raise_if_inconsistent()`."""


def _replay_expected_positions(conn: sqlite3.Connection) -> dict[str, Decimal]:
    """Reconstruct expected open-position quantities purely from `audit_log`,
    in timestamp order -- never reading `positions` itself, so this is a
    genuinely independent second source, not a comparison of a table against
    itself.
    """
    rows = conn.execute(
        "SELECT event_type, payload_json FROM audit_log "
        "WHERE event_type IN ('entry_filled', 'position_closed') ORDER BY ts_utc, id"
    ).fetchall()
    expected: dict[str, Decimal] = {}
    for event_type, payload_json in rows:
        payload = json.loads(payload_json)
        key = f"{payload['market']}:{payload['symbol']}:{payload['sleeve']}"
        if event_type == "entry_filled":
            expected[key] = Decimal(payload["qty"])
        elif event_type == "position_closed":
            expected.pop(key, None)
    return expected


def _actual_positions(conn: sqlite3.Connection) -> dict[str, Decimal]:
    rows = conn.execute("SELECT market, symbol, sleeve, qty FROM positions").fetchall()
    return {f"{market}:{symbol}:{sleeve}": Decimal(qty) for market, symbol, sleeve, qty in rows}


def reconcile(conn: sqlite3.Connection) -> ReconciliationResult:
    """Compare `positions` (PaperBroker's reported state) against the
    independent replay of `audit_log`. `ok=False` means the two sources
    disagree -- a bug, not a tolerance to paper over.
    """
    expected = _replay_expected_positions(conn)
    actual = _actual_positions(conn)
    keys = set(expected) | set(actual)
    mismatches = [
        Mismatch(key, expected.get(key), actual.get(key))
        for key in sorted(keys)
        if expected.get(key) != actual.get(key)
    ]
    return ReconciliationResult(ok=len(mismatches) == 0, mismatches=tuple(mismatches))
