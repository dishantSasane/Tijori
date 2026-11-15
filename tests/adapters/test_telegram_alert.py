from __future__ import annotations

from datetime import UTC, datetime

import pytest

from trading.adapters.telegram_alert import DecisionState, FakeTelegramAlerts, SignalDecisionBoard
from trading.storage.state_store import StateStore

NOW = datetime(2026, 1, 5, 5, 0, tzinfo=UTC)


@pytest.fixture
def store(tmp_path):
    s = StateStore(tmp_path / "tg.db")
    yield s
    s.close()


@pytest.fixture
def board(store) -> SignalDecisionBoard:
    return SignalDecisionBoard(store)


def test_no_live_network_calls_in_fake():
    fake = FakeTelegramAlerts()
    message_id = fake.send_card("sig-1", "entry card")
    assert message_id.startswith("msg-")
    fake.edit_card(message_id, "-> Approved")
    assert fake.sent == [("sig-1", "entry card", None)]
    assert fake.edits == [(message_id, "-> Approved")]


def test_pending_to_approved_transition(board):
    board.open_card("sig-1", "msg-1", batch_id=None, now=NOW)
    assert board.state("sig-1") == DecisionState.PENDING
    changed = board.decide("sig-1", DecisionState.APPROVED, decided_by="telegram", now=NOW)
    assert changed
    assert board.state("sig-1") == DecisionState.APPROVED


def test_double_tap_on_terminal_card_is_a_noop(board, store):
    board.open_card("sig-1", "msg-1", batch_id=None, now=NOW)
    board.decide("sig-1", DecisionState.REJECTED, decided_by="telegram", now=NOW)
    changed_again = board.decide("sig-1", DecisionState.APPROVED, decided_by="telegram", now=NOW)
    assert not changed_again
    assert board.state("sig-1") == DecisionState.REJECTED  # unchanged
    assert store.audit_events("telegram_decision_ignored_terminal")


def test_race_between_two_surfaces_first_writer_wins(board):
    board.open_card("sig-1", "msg-1", batch_id=None, now=NOW)
    telegram_won = board.decide("sig-1", DecisionState.APPROVED, decided_by="telegram", now=NOW)
    dashboard_lost = board.decide("sig-1", DecisionState.REJECTED, decided_by="dashboard", now=NOW)
    assert telegram_won
    assert not dashboard_lost
    assert board.state("sig-1") == DecisionState.APPROVED
