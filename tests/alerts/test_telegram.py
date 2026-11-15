from __future__ import annotations

from datetime import UTC, datetime

from trading.alerts.telegram import DecisionState, LoggingMessageSender, TelegramDecisionStore
from trading.risk.audit import AuditLog
from trading.storage.state_db import connect

T0 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)


def _store():
    conn = connect(":memory:")
    audit = AuditLog(conn)
    sender = LoggingMessageSender()
    return TelegramDecisionStore(conn, audit, sender), sender


def test_submit_starts_pending() -> None:
    store, sender = _store()
    store.submit("sig-1", "card text", batch_id=None, now=T0)
    assert store.state("sig-1") == DecisionState.PENDING
    assert sender.sent == ["card text"]


def test_approve_transitions_to_approved_and_edits_card() -> None:
    store, sender = _store()
    store.submit("sig-1", "card text", batch_id=None, now=T0)
    won = store.decide("sig-1", "approve", decided_by="owner", now=T0)
    assert won is True
    assert store.state("sig-1") == DecisionState.APPROVED
    assert len(sender.edits) == 1


def test_double_tap_is_a_noop_not_a_second_decision() -> None:
    store, _ = _store()
    store.submit("sig-1", "card text", batch_id=None, now=T0)
    first = store.decide("sig-1", "approve", decided_by="owner", now=T0)
    second = store.decide("sig-1", "reject", decided_by="owner", now=T0)
    assert first is True
    assert second is False
    assert store.state("sig-1") == DecisionState.APPROVED  # unchanged by the second tap


def test_telegram_vs_dashboard_race_only_one_wins() -> None:
    store, _ = _store()
    store.submit("sig-1", "card text", batch_id=None, now=T0)
    telegram_wins = store.decide("sig-1", "approve", decided_by="telegram:owner", now=T0)
    dashboard_wins = store.decide("sig-1", "reject", decided_by="dashboard:owner", now=T0)
    assert telegram_wins is True
    assert dashboard_wins is False
    assert store.state("sig-1") == DecisionState.APPROVED


def test_expire_only_affects_still_pending_rows() -> None:
    store, _ = _store()
    store.submit("sig-1", "card text", batch_id=None, now=T0)
    store.decide("sig-1", "approve", decided_by="owner", now=T0)
    expired = store.expire("sig-1", now=T0)
    assert expired is False  # already terminal; expiry must not override a real decision
    assert store.state("sig-1") == DecisionState.APPROVED


def test_expire_pending_signal() -> None:
    store, _ = _store()
    store.submit("sig-2", "card text", batch_id=None, now=T0)
    expired = store.expire("sig-2", now=T0)
    assert expired is True
    assert store.state("sig-2") == DecisionState.EXPIRED


def test_batch_assignment_does_not_cross_contaminate_decisions() -> None:
    store, _ = _store()
    store.submit("sig-1", "a", batch_id=None, now=T0)
    store.submit("sig-2", "b", batch_id=None, now=T0)
    store.assign_batch(["sig-1", "sig-2"], "batch-1")
    store.decide("sig-1", "approve", decided_by="owner", now=T0)
    assert store.state("sig-1") == DecisionState.APPROVED
    assert store.state("sig-2") == DecisionState.PENDING  # batch assignment != blanket decision
