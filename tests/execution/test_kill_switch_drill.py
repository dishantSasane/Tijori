"""The P2 exit-criterion kill-switch drill, as an automated test.

docs/specs/PAPER_BROKER_SPEC.md §6, six steps. This is a *demonstrated run*,
not just a unit test of one function: it drives the real `PaperBroker` +
`StateStore` + `KillSwitch` through open position -> engage -> block ->
persist -> release -> resume, including a restart between engage and check.
"""

from __future__ import annotations

from decimal import Decimal

from tests.execution.conftest import make_candle, make_decision, make_signal
from trading.backtest.fills import BacktestProfile
from trading.core.clock import FixedClock
from trading.execution.paper_broker import PaperBroker, PaperBrokerHaltedError
from trading.risk.kill_switch import GLOBAL_SCOPE, KillSwitch


def test_kill_switch_drill_full_six_steps(tmp_path):
    from tests.execution.conftest import NOW
    from trading.storage.state_store import StateStore

    db_path = tmp_path / "drill.db"
    clock = FixedClock(at=NOW)

    # --- Step 1: one open position, one pending signal. ---
    store = StateStore(db_path)
    kill_switch = KillSwitch(store, clock=clock)
    broker = PaperBroker(store, kill_switch, clock=clock)

    open_signal = make_signal(symbol="OPEN_POS")
    broker.submit_entry(open_signal, make_decision(open_signal), profile=BacktestProfile())
    broker.on_closed_candle(
        make_candle(Decimal(2500), Decimal(2510), Decimal(2495), Decimal(2505), symbol="OPEN_POS")
    )
    assert len(store.positions()) == 1  # now a live stop-protected position

    pending_signal = make_signal(symbol="PENDING_SIG")
    broker.submit_entry(pending_signal, make_decision(pending_signal), profile=BacktestProfile())
    assert pending_signal.id in store.pending_fill_ids()

    # --- Step 2: engage the kill switch (manual path). ---
    kill_switch.engage(GLOBAL_SCOPE, "manual_drill", actor="dishant")

    # --- Step 4 (checked before step 3's assertions, per the spec's ordering note): ---
    assert kill_switch.is_engaged(GLOBAL_SCOPE)
    assert store.audit_events("kill_switch_engaged")

    # --- Step 3: zero new entries; cancel open entry orders; stops stay live. ---
    new_signal = make_signal(symbol="NEW_SIG")
    try:
        broker.submit_entry(new_signal, make_decision(new_signal), profile=BacktestProfile())
        raised = False
    except PaperBrokerHaltedError:
        raised = True
    assert raised, "a new entry must be blocked while the kill switch is engaged (I6)"

    cancelled = broker.cancel_pending_entries(GLOBAL_SCOPE, reason="manual_drill")
    assert cancelled == [pending_signal.id]
    assert store.pending_fill_ids() == []  # the pending entry was cancelled

    # The open position's protective stop is untouched and still fires.
    assert len(store.positions()) == 1
    broker.on_closed_candle(
        make_candle(Decimal(2440), Decimal(2445), Decimal(2430), Decimal(2440), symbol="OPEN_POS")
    )
    assert store.positions() == []  # the stop fired even with the kill switch engaged
    store.close()

    # --- Step 6: restart between engage and the re-check. ---
    store2 = StateStore(db_path)
    kill_switch2 = KillSwitch(store2, clock=clock)
    broker2 = PaperBroker(store2, kill_switch2, clock=clock)
    assert kill_switch2.is_engaged(GLOBAL_SCOPE)  # survived restart
    another_signal = make_signal(symbol="AFTER_RESTART")
    try:
        broker2.submit_entry(
            another_signal, make_decision(another_signal), profile=BacktestProfile()
        )
        raised = False
    except PaperBrokerHaltedError:
        raised = True
    assert raised

    # --- Step 5: release via explicit human action; new entries resume. ---
    kill_switch2.disengage(GLOBAL_SCOPE, actor="dishant")
    released_events = store2.audit_events("kill_switch_released")
    assert len(released_events) == 1
    assert released_events[0]["actor"] == "dishant"

    resumed_signal = make_signal(symbol="RESUMED")
    order = broker2.submit_entry(
        resumed_signal, make_decision(resumed_signal), profile=BacktestProfile()
    )
    assert order.status.value == "risk_approved"
    store2.close()


def test_kill_release_never_implicit(store, kill_switch, clock):
    """Time passing / a restart never flips `engaged` back to False by itself."""
    kill_switch.engage(GLOBAL_SCOPE, "drill")
    clock.advance(seconds=3600 * 24)
    assert kill_switch.is_engaged(GLOBAL_SCOPE)


def test_kill_automatic_trigger_same_shape_as_manual(store, clock):
    manual = KillSwitch(store, clock=clock)
    manual.engage(GLOBAL_SCOPE, "manual_reason", actor="dishant")
    manual_event = store.audit_events("kill_switch_engaged")[0]

    automatic = KillSwitch(store, clock=clock)
    automatic.engage("sleeve:in_equity", "max_daily_loss_pct_breached", actor="system")
    auto_event = store.audit_events("kill_switch_engaged")[1]

    assert set(manual_event["payload"]) == set(auto_event["payload"])
    assert auto_event["actor"] == "system"
    assert manual_event["actor"] == "dishant"
