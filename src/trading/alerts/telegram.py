"""Telegram/dashboard decision state machine: docs/specs/TELEGRAM_ALERT_SPEC.md.

Paper-only wiring (BUILD_ORDER.md P2: "Telegram alert ... paper-only wiring
first"). `MessageSender` is a thin Protocol so a real Telegram bot can be
plugged in later without touching this state machine -- `LoggingMessageSender`
is the stand-in until the owner provides a bot token (AGENTS.md §4.3: keys
live in `.env`, never read here).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from trading.risk.audit import AuditLog


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

_ACTION_TO_STATE = {
    "approve": DecisionState.APPROVED,
    "paper_test": DecisionState.PAPER_TESTED,
    "reject": DecisionState.REJECTED,
}


class MessageSender(Protocol):
    def send_card(self, text: str) -> str:
        """Send a card, return a message id."""
        ...

    def edit_card(self, message_id: str, text: str) -> None: ...


class LoggingMessageSender:
    """Stand-in until a real Telegram bot token exists. Records sent/edited
    text in memory so tests (and the owner, via logs) can see exactly what
    would have gone out.
    """

    def __init__(self) -> None:
        self.sent: list[str] = []
        self.edits: dict[str, str] = {}
        self._next_id = 0

    def send_card(self, text: str) -> str:
        self._next_id += 1
        message_id = f"msg-{self._next_id}"
        self.sent.append(text)
        return message_id

    def edit_card(self, message_id: str, text: str) -> None:
        self.edits[message_id] = text


class DecisionAlreadyMadeError(RuntimeError):
    """Raised when a caller tries to act on a signal that is no longer PENDING."""


class TelegramDecisionStore:
    """docs/specs/TELEGRAM_ALERT_SPEC.md §2-4: 5-state machine, pre-market
    batching, and optimistic-write concurrency between Telegram and the
    dashboard (both call `decide`, both hit the same row).
    """

    def __init__(self, conn: sqlite3.Connection, audit: AuditLog, sender: MessageSender) -> None:
        self._conn = conn
        self._audit = audit
        self._sender = sender

    def submit(self, signal_id: str, card_text: str, *, batch_id: str | None, now: datetime) -> str:
        message_id = self._sender.send_card(card_text)
        self._conn.execute(
            "INSERT INTO telegram_decisions "
            "(signal_id, state, batch_id, message_id, decided_by, decided_ts) "
            "VALUES (?, ?, ?, ?, NULL, NULL)",
            (signal_id, DecisionState.PENDING.value, batch_id, message_id),
        )
        self._conn.commit()
        return message_id

    def state(self, signal_id: str) -> DecisionState | None:
        row = self._conn.execute(
            "SELECT state FROM telegram_decisions WHERE signal_id = ?", (signal_id,)
        ).fetchone()
        return DecisionState(row[0]) if row else None

    def decide(self, signal_id: str, action: str, *, decided_by: str, now: datetime) -> bool:
        """Apply a human decision. Returns True if this call actually made
        the transition, False if the row was already terminal (a double-tap
        or a race the other surface won) -- callers must not raise on False,
        just stop quietly (§4).
        """
        new_state = _ACTION_TO_STATE[action]
        cur = self._conn.execute(
            "UPDATE telegram_decisions SET state = ?, decided_by = ?, decided_ts = ? "
            "WHERE signal_id = ? AND state = ?",
            (new_state.value, decided_by, now.isoformat(), signal_id, DecisionState.PENDING.value),
        )
        self._conn.commit()
        won = cur.rowcount > 0
        if won:
            self._audit.write(
                ts_utc=now,
                event_type="telegram_decision_made",
                actor=decided_by,
                payload={"signal_id": signal_id, "action": action},
            )
            row = self._conn.execute(
                "SELECT message_id FROM telegram_decisions WHERE signal_id = ?", (signal_id,)
            ).fetchone()
            if row and row[0]:
                self._sender.edit_card(
                    row[0], f"-> {new_state.value} by {decided_by} at {now.isoformat()}"
                )
        else:
            self._audit.write(
                ts_utc=now,
                event_type="telegram_decision_already_made",
                actor=decided_by,
                payload={"signal_id": signal_id, "attempted_action": action},
            )
        return won

    def expire(self, signal_id: str, *, now: datetime) -> bool:
        cur = self._conn.execute(
            "UPDATE telegram_decisions SET state = ?, decided_ts = ? "
            "WHERE signal_id = ? AND state = ?",
            (DecisionState.EXPIRED.value, now.isoformat(), signal_id, DecisionState.PENDING.value),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def pending_for_batch(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT signal_id FROM telegram_decisions WHERE state = ? AND batch_id IS NULL",
            (DecisionState.PENDING.value,),
        ).fetchall()
        return [r[0] for r in rows]

    def assign_batch(self, signal_ids: list[str], batch_id: str) -> None:
        self._conn.executemany(
            "UPDATE telegram_decisions SET batch_id = ? WHERE signal_id = ?",
            [(batch_id, sid) for sid in signal_ids],
        )
        self._conn.commit()
