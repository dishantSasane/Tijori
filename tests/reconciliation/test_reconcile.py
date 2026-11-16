"""Reconciliation tests. Only a fake position source is used — never a real
broker (AGENTS.md §4.4) — because this tests a pure comparison function and
its kill-switch side effect, not any network call.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from trading.reconciliation.reconcile import BrokerPosition, reconcile, run_drill
from trading.risk.audit import AuditLog
from trading.risk.kill_switch import KillSwitch
from trading.storage.state_db import connect

NOW = datetime(2026, 11, 16, tzinfo=UTC)


@dataclass(frozen=True)
class FakeLocal:
    market: str
    symbol: str
    qty: Decimal


def test_reconcile_clean_when_both_sides_agree() -> None:
    local = [FakeLocal("NSE", "RELIANCE", Decimal(10))]
    broker = [BrokerPosition("NSE", "RELIANCE", Decimal(10))]
    report = reconcile(local, broker, now=NOW)
    assert report.clean
    assert report.mismatches == ()


def test_reconcile_flags_qty_mismatch() -> None:
    local = [FakeLocal("NSE", "RELIANCE", Decimal(10))]
    broker = [BrokerPosition("NSE", "RELIANCE", Decimal(5))]
    report = reconcile(local, broker, now=NOW)
    assert not report.clean
    assert report.mismatches[0].local_qty == Decimal(10)
    assert report.mismatches[0].broker_qty == Decimal(5)


def test_reconcile_flags_position_missing_on_broker_side() -> None:
    local = [FakeLocal("NSE", "RELIANCE", Decimal(10))]
    report = reconcile(local, [], now=NOW)
    assert not report.clean
    assert report.mismatches[0].broker_qty is None


def test_reconcile_flags_position_missing_locally() -> None:
    broker = [BrokerPosition("NSE", "RELIANCE", Decimal(10))]
    report = reconcile([], broker, now=NOW)
    assert not report.clean
    assert report.mismatches[0].local_qty is None


def test_reconcile_flags_duplicate_rows_instead_of_overwriting_them() -> None:
    local = [FakeLocal("NSE", "RELIANCE", Decimal(10)), FakeLocal("NSE", "RELIANCE", Decimal(10))]
    broker = [BrokerPosition("NSE", "RELIANCE", Decimal(10))]
    report = reconcile(local, broker, now=NOW)
    assert not report.clean
    assert report.mismatches[0].reason == "duplicate_local_position"


def test_run_drill_engages_kill_switch_on_mismatch_and_leaves_it_off_when_clean() -> None:
    conn = connect(":memory:")
    audit = AuditLog(conn)
    kill_switch = KillSwitch(conn, audit)

    # Clean case: no engagement.
    local = [FakeLocal("NSE", "RELIANCE", Decimal(10))]
    broker = [BrokerPosition("NSE", "RELIANCE", Decimal(10))]
    report = run_drill(local, broker, audit=audit, kill_switch=kill_switch, now=NOW)
    assert report.clean
    assert not kill_switch.is_engaged("global")

    # Mismatch case: kill switch engages, blocking new entries (checked first
    # by RiskEngine.check per RISK_ENGINE_SPEC.md §2).
    broker_bad = [BrokerPosition("NSE", "RELIANCE", Decimal(999))]
    report2 = run_drill(local, broker_bad, audit=audit, kill_switch=kill_switch, now=NOW)
    assert not report2.clean
    assert kill_switch.is_engaged("global")

    events = audit.events(event_type="reconciliation_drill")
    assert len(events) == 2


def demo() -> None:
    """Runnable self-check (ponytail: smallest thing that fails if the
    comparison logic breaks).
    """
    assert reconcile(
        [FakeLocal("NSE", "TCS", Decimal(1))],
        [BrokerPosition("NSE", "TCS", Decimal(1))],
        now=NOW,
    ).clean
    assert not reconcile(
        [FakeLocal("NSE", "TCS", Decimal(1))],
        [BrokerPosition("NSE", "TCS", Decimal(2))],
        now=NOW,
    ).clean
    print("reconciliation demo OK")


if __name__ == "__main__":
    demo()
