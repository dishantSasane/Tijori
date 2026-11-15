"""TelegramAlerts Protocol + fake, and the per-signal decision state machine.

docs/specs/TELEGRAM_ALERT_SPEC.md §2 (PENDING -> APPROVED/PAPER_TESTED/
REJECTED/EXPIRED). Paper-only wiring first (AGENTS.md, BUILD_ORDER.md P2):
Approve only ever requests `Route.LIVE` through `ModeGate`, which itself
still refuses it unless the sleeve is in `approval`/`auto` mode (AGENTS.md
§4.1) — this module never talks to a real broker.

The real `python-telegram-bot` wiring is an adapter behind `TelegramAlerts`;
tests use `FakeTelegramAlerts` only, so no live bot token is ever required to
run the suite (AGENTS.md §4.4).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Protocol

from trading.storage.state_store import StateStore


class DecisionState(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    PAPER_TESTED = "paper_tested"
    REJECTED = "rejected"
    EXPIRED = "expired"


_TERMINAL = {
    DecisionState.APPROVED,
    DecisionState.PAPER_TESTED,
    DecisionState.REJECTED,
    DecisionState.EXPIRED,
}


class TelegramAlerts(Protocol):
    def send_card(self, signal_id: str, text: str, *, batch_id: str | None = None) -> str:
        """Send an Approve/Paper-test/Reject card; returns a message id."""
        ...

    def edit_card(self, message_id: str, text: str) -> None:
        """Edit a resolved card to show its outcome, removing the keyboard."""
        ...


class FakeTelegramAlerts:
    """In-memory fake. Records every card sent/edited; no network calls ever."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str | None]] = []
        self.edits: list[tuple[str, str]] = []
        self._next_id = 0

    def send_card(self, signal_id: str, text: str, *, batch_id: str | None = None) -> str:
        self._next_id += 1
        message_id = f"msg-{self._next_id}"
        self.sent.append((signal_id, text, batch_id))
        return message_id

    def edit_card(self, message_id: str, text: str) -> None:
        self.edits.append((message_id, text))


class SignalDecisionBoard:
    """Backs `telegram_decisions` (TELEGRAM_ALERT_SPEC.md §2). Both Telegram
    and a future dashboard write through `decide()` — optimistic check on
    `state`, first writer wins (§4), always audited.
    """

    def __init__(self, store: StateStore) -> None:
        self._store = store
        self._conn = store._conn  # noqa: SLF001 - same module family, no public cursor API yet

    def open_card(
        self, signal_id: str, message_id: str, *, batch_id: str | None, now: datetime
    ) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO telegram_decisions "
            "(signal_id, state, batch_id, message_id, decided_by, decided_ts) "
            "VALUES (?, ?, ?, ?, NULL, NULL)",
            (signal_id, DecisionState.PENDING.value, batch_id, message_id),
        )
        self._conn.commit()

    def state(self, signal_id: str) -> DecisionState:
        row = self._conn.execute(
            "SELECT state FROM telegram_decisions WHERE signal_id=?", (signal_id,)
        ).fetchone()
        return DecisionState(row[0]) if row else DecisionState.PENDING

    def decide(
        self, signal_id: str, new_state: DecisionState, *, decided_by: str, now: datetime
    ) -> bool:
        """Returns True if this call made the transition; False if the card
        was already terminal (a no-op, per §4 — never a second AuditEvent for
        the same resolution, but the caller still gets a clean answer).
        """
        cur = self._conn.execute(
            "UPDATE telegram_decisions SET state=?, decided_by=?, decided_ts=? "
            "WHERE signal_id=? AND state=?",
            (new_state.value, decided_by, now.isoformat(), signal_id, DecisionState.PENDING.value),
        )
        self._conn.commit()
        changed = cur.rowcount > 0
        self._store.write_audit(
            event_type="telegram_decision" if changed else "telegram_decision_ignored_terminal",
            actor=decided_by,
            payload={"signal_id": signal_id, "new_state": new_state.value},
            ts=now,
        )
        return changed
