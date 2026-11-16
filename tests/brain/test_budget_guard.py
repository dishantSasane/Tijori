from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trading.brain.budget_guard import BudgetGuard
from trading.storage.state_db import connect

TS = datetime(2026, 6, 15, 10, 0, tzinfo=UTC)


@pytest.fixture
def guard():
    conn = connect(":memory:")
    return BudgetGuard(conn, daily_cap_inr=Decimal(50), monthly_cap_inr=Decimal(500))


def test_allows_call_when_under_both_caps(guard):
    assert guard.allow(TS) is True


def test_blocks_when_daily_cap_reached(guard):
    guard.record_call(
        now=TS,
        provider="anthropic",
        model="claude-x",
        purpose="signal_context_verdict",
        tokens_in=100,
        tokens_out=50,
        cost_inr=Decimal(50),
        signal_id="s1",
        ok=True,
    )
    assert guard.allow(TS) is False


def test_blocks_at_exact_cap_not_only_above(guard):
    guard.record_call(
        now=TS,
        provider="anthropic",
        model="claude-x",
        purpose="signal_context_verdict",
        tokens_in=1,
        tokens_out=1,
        cost_inr=Decimal(50),
        signal_id="s1",
        ok=True,
    )
    status = guard.status(TS)
    assert status.spent_today_inr == Decimal(50)
    assert status.allowed is False  # 100% spent -> off, per BRAIN_AND_COSTS.md §5


def test_spend_yesterday_does_not_count_against_today(guard):
    yesterday = TS.replace(day=14)
    guard.record_call(
        now=yesterday,
        provider="anthropic",
        model="claude-x",
        purpose="signal_context_verdict",
        tokens_in=1,
        tokens_out=1,
        cost_inr=Decimal(50),
        signal_id="s1",
        ok=True,
    )
    assert guard.allow(TS) is True  # new day, daily cap resets
    # but the monthly cap still sees it
    assert guard.status(TS).spent_month_inr == Decimal(50)


def test_monthly_cap_blocks_even_with_daily_room(guard):
    guard2 = BudgetGuard(guard._conn, daily_cap_inr=Decimal(1000), monthly_cap_inr=Decimal(50))
    guard2.record_call(
        now=TS.replace(day=1),
        provider="anthropic",
        model="claude-x",
        purpose="signal_context_verdict",
        tokens_in=1,
        tokens_out=1,
        cost_inr=Decimal(50),
        signal_id="s1",
        ok=True,
    )
    assert guard2.allow(TS) is False


def test_failed_calls_still_counted_if_recorded_with_cost(guard):
    guard.record_call(
        now=TS,
        provider="anthropic",
        model="claude-x",
        purpose="signal_context_verdict",
        tokens_in=10,
        tokens_out=0,
        cost_inr=Decimal(1),
        signal_id="s1",
        ok=False,
    )
    assert guard.status(TS).spent_today_inr == Decimal(1)
