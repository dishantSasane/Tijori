"""The automated form of docs/specs/PAPER_BROKER_SPEC.md §6's 6-step drill,
per docs/specs/TEST_SPEC_RISK.md §8. Exercises the real PaperBroker (not
FakePaperBroker) against SQLite so persistence/restart are genuinely tested.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading.backtest.fills import BacktestProfile
from trading.broker.paper_broker import PaperBroker
from trading.core.enums import (
    LedgerSource,
    MarketId,
    Mode,
    OrderSide,
    OutcomeResult,
    ReasonCode,
    Route,
    Timeframe,
)
from trading.core.models import Signal
from trading.risk.audit import AuditLog
from trading.risk.decision_store import DecisionStore
from trading.risk.engine import ModeGate, RiskEngine
from trading.risk.fakes import FakeDataFreshness, FakeSessionCalendar
from trading.risk.kill_switch import KillSwitch
from trading.risk.portfolio import PortfolioState, RiskConfig, SleeveState
from trading.storage.state_db import connect

MKT = MarketId.IN_EQUITY.value
T0 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)


def _signal(signal_id_suffix: str, bar_ts, *, symbol: str = "HDFCBANK") -> Signal:
    return Signal(
        id=f"sig-{signal_id_suffix}",
        market=MarketId.IN_EQUITY,
        symbol=symbol,
        timeframe=Timeframe.D1,
        strategy_id="t1",
        strategy_version="1.0.0",
        side=OrderSide.BUY,
        entry_ref=Decimal(2500),
        stop=Decimal(2450),
        bar_ts_utc=bar_ts,
        created_ts=bar_ts,
    )


def _rig(db_path):
    conn = connect(db_path)
    audit = AuditLog(conn)
    kill_switch = KillSwitch(conn, audit)
    decisions = DecisionStore(conn)
    calendar = FakeSessionCalendar(open_markets={MKT})
    freshness = FakeDataFreshness()
    engine = RiskEngine(
        kill_switch=kill_switch, decision_store=decisions, calendar=calendar, freshness=freshness
    )
    profile = BacktestProfile(brokerage=Decimal(0), slippage_bps=Decimal(0))
    broker = PaperBroker(conn, audit, profile=profile)
    portfolio = PortfolioState(
        sleeves={
            "india_equity": SleeveState(
                equity=Decimal(1_000_000),
                open_positions=0,
                daily_pnl_pct=Decimal(0),
                allocation_used_pct=Decimal(10),
                allocation_cap_pct=Decimal(40),
                max_positions=6,
            )
        },
        total_open_positions=0,
        portfolio_peak_equity=Decimal(1_000_000),
        portfolio_equity=Decimal(1_000_000),
    )
    config = RiskConfig(
        market=MarketId.IN_EQUITY,
        sleeve_mode=Mode.PAPER,
        risk_per_trade_pct=Decimal("0.5"),
        max_position_value_pct=Decimal(100),
        max_risk_distance_pct_of_entry=Decimal(10),
        order_price_band_pct=Decimal(5),
        stale_data_seconds=30,
        max_portfolio_drawdown_pct=Decimal(10),
        max_daily_loss_pct=Decimal(2),
    )
    return engine, kill_switch, broker, portfolio, config


def test_six_step_kill_switch_drill(tmp_path) -> None:
    db_path = tmp_path / "drill.db"
    engine, kill_switch, broker, portfolio, config = _rig(db_path)

    # Step 1: one open position, one pending signal.
    open_signal = _signal("open-pos", T0)
    d1 = engine.check(open_signal, portfolio, None, config, sleeve="india_equity", now=T0)
    assert d1.allowed is True
    broker.accept(
        open_signal,
        qty=d1.qty,
        sleeve="india_equity",
        ledger_source=LedgerSource.USER_PAPER,
        now=T0,
    )
    t1 = T0 + timedelta(days=1)
    broker.on_candle(
        market=MKT,
        symbol="HDFCBANK",
        ts_open_utc=t1,
        open_=Decimal(2500),
        high=Decimal(2505),
        low=Decimal(2495),
        now=t1,
    )
    assert len(broker.open_positions()) == 1  # now an open position, not pending

    pending_signal = _signal("pending", t1)
    d2 = engine.check(pending_signal, portfolio, None, config, sleeve="india_equity", now=t1)
    assert d2.allowed is True
    broker.accept(
        pending_signal,
        qty=d2.qty,
        sleeve="india_equity",
        ledger_source=LedgerSource.USER_PAPER,
        now=t1,
    )
    assert len(broker.pending_signals()) == 1

    # Step 2: engage the kill switch (manual path here; automatic path covered
    # separately below).
    kill_switch.engage("global", "manual_drill", actor="owner", now=t1)

    # Step 4 (checked before step 3's assertions, per the drill's ordering):
    # the engagement is persisted and audited before we rely on its effect.
    assert kill_switch.is_engaged("global") is True
    engage_events = broker.audit.events(event_type="kill_switch_engaged")
    assert len(engage_events) == 1

    # Step 3: zero new entries accepted; existing pending entry cancelled;
    # the already-open position's stop remains live.
    new_signal = _signal("after-kill", t1)
    d3 = engine.check(new_signal, portfolio, None, config, sleeve="india_equity", now=t1)
    assert d3.allowed is False
    assert d3.reason_codes == (ReasonCode.KILL_SWITCH_ENGAGED,)

    cancelled = broker.cancel_all_pending_entries(reason="kill_switch_engaged", now=t1)
    assert cancelled == [pending_signal.id]
    assert broker.pending_signals() == []
    assert len(broker.open_positions()) == 1  # the earlier open position + its stop are untouched

    t2 = t1 + timedelta(days=1)
    broker.on_candle(
        market=MKT,
        symbol="HDFCBANK",
        ts_open_utc=t2,
        open_=Decimal(2400),
        high=Decimal(2410),
        low=Decimal(2390),
        now=t2,
    )
    assert (
        broker.open_positions() == []
    )  # the stop still fired even though the kill switch is engaged
    assert broker.outcome(open_signal.id) == OutcomeResult.STOP_HIT

    # Step 6: restart between engagement and the next check -- re-run step 3's
    # assertion against a fresh engine/broker pair over the same SQLite file.
    engine2, kill_switch2, broker2, portfolio2, config2 = _rig(db_path)
    assert kill_switch2.is_engaged("global") is True
    d_after_restart = engine2.check(
        _signal("post-restart", t2), portfolio2, None, config2, sleeve="india_equity", now=t2
    )
    assert d_after_restart.allowed is False
    assert d_after_restart.reason_codes == (ReasonCode.KILL_SWITCH_ENGAGED,)

    # Step 5: release via the explicit human-action path; entries resume and
    # the release is itself audited.
    kill_switch2.release("global", actor="owner", now=t2)
    assert kill_switch2.is_engaged("global") is False
    release_events = broker2.audit.events(event_type="kill_switch_released")
    assert len(release_events) == 1
    resumed = _signal("after-release", t2)
    d_resumed = engine2.check(resumed, portfolio2, None, config2, sleeve="india_equity", now=t2)
    assert d_resumed.allowed is True


def _setup_one_open_position_one_pending(db_path, now: datetime):
    """Common step-1 fixture for the granular test vectors below: one open
    position (stop live) and one separate pending (unfilled) signal.
    """
    engine, kill_switch, broker, portfolio, config = _rig(db_path)
    open_signal = _signal("open-pos", now)
    d1 = engine.check(open_signal, portfolio, None, config, sleeve="india_equity", now=now)
    assert d1.allowed is True
    broker.accept(
        open_signal,
        qty=d1.qty,
        sleeve="india_equity",
        ledger_source=LedgerSource.USER_PAPER,
        now=now,
    )
    t1 = now + timedelta(days=1)
    broker.on_candle(
        market=MKT,
        symbol="HDFCBANK",
        ts_open_utc=t1,
        open_=Decimal(2500),
        high=Decimal(2505),
        low=Decimal(2495),
        now=t1,
    )
    assert len(broker.open_positions()) == 1

    # A different symbol than the already-open position -- PaperBroker keys
    # one open position per (market, symbol, sleeve), and this fixture's job
    # is to exercise "one open + one separately pending," not the same-symbol
    # overlap guard.
    pending_signal = _signal("pending", t1, symbol="ICICIBANK")
    d2 = engine.check(pending_signal, portfolio, None, config, sleeve="india_equity", now=t1)
    assert d2.allowed is True
    broker.accept(
        pending_signal,
        qty=d2.qty,
        sleeve="india_equity",
        ledger_source=LedgerSource.USER_PAPER,
        now=t1,
    )
    assert len(broker.pending_signals()) == 1
    return engine, kill_switch, broker, portfolio, config, open_signal, pending_signal, t1


def test_kill_engage_blocks_new_entries_immediately(tmp_path) -> None:
    """Step 3, I6: with one open position and one PENDING signal already
    accepted, engage the kill switch, then submit a second, otherwise-
    approvable signal -> rejected, zero new pending_fills rows.
    """
    engine, kill_switch, broker, portfolio, config, _, _, t1 = _setup_one_open_position_one_pending(
        tmp_path / "db1.db", T0
    )
    kill_switch.engage("global", "manual_drill", actor="owner", now=t1)
    pending_before = len(broker.pending_signals())

    new_signal = _signal("after-kill", t1)
    decision = engine.check(new_signal, portfolio, None, config, sleeve="india_equity", now=t1)
    assert decision.allowed is False
    assert decision.reason_codes == (ReasonCode.KILL_SWITCH_ENGAGED,)
    # A rejected decision is never passed to broker.accept() by the caller --
    # nothing new enters pending_fills.
    assert len(broker.pending_signals()) == pending_before


def test_kill_engage_cancels_open_entry_orders_not_stops(tmp_path) -> None:
    """Step 3: the pending entry is cancelled; the open position's protective
    stop is untouched and still live. This PaperBroker tracks a pending entry
    as a `pending_fills` row rather than an `Order`+`transition()` state
    machine, so "cancelled" here means removed from `pending_fills` with an
    audit event -- the same invariant RISK_SPEC.md §4's carve-out describes,
    expressed in this broker's actual data model.
    """
    engine, kill_switch, broker, portfolio, config, open_signal, pending_signal, t1 = (
        _setup_one_open_position_one_pending(tmp_path / "db2.db", T0)
    )
    kill_switch.engage("global", "manual_drill", actor="owner", now=t1)

    cancelled = broker.cancel_all_pending_entries(reason="kill_switch_engaged", now=t1)
    assert cancelled == [pending_signal.id]
    assert broker.pending_signals() == []
    cancel_events = broker.audit.events(event_type="pending_entry_cancelled")
    assert len(cancel_events) == 1

    # The open position + its stop are untouched by the cancellation...
    assert len(broker.open_positions()) == 1
    # ...and the stop still fires on the next candle that trades through it,
    # even with the kill switch engaged.
    t2 = t1 + timedelta(days=1)
    broker.on_candle(
        market=MKT,
        symbol="HDFCBANK",
        ts_open_utc=t2,
        open_=Decimal(2400),
        high=Decimal(2410),
        low=Decimal(2390),
        now=t2,
    )
    assert broker.open_positions() == []
    assert broker.outcome(open_signal.id) == OutcomeResult.STOP_HIT


def test_kill_engagement_persists_before_block_takes_effect(tmp_path) -> None:
    """Step 4: the engagement is persisted and audited -- checked first --
    before relying on its effect to reject the next signal.
    """
    engine, kill_switch, broker, portfolio, config, _, _, t1 = _setup_one_open_position_one_pending(
        tmp_path / "db3.db", T0
    )
    kill_switch.engage("global", "manual_drill", actor="owner", now=t1)

    # Persistence/audit checked first, deliberately, before the rejection
    # that depends on it.
    assert kill_switch.is_engaged("global") is True
    engage_events = broker.audit.events(event_type="kill_switch_engaged")
    assert len(engage_events) == 1
    assert engage_events[0]["actor"] == "owner"

    # Only now does the test rely on the engagement's effect.
    decision = engine.check(
        _signal("after", t1), portfolio, None, config, sleeve="india_equity", now=t1
    )
    assert decision.allowed is False


def test_kill_release_resumes_entries_and_is_audited(tmp_path) -> None:
    """Step 5, I10: release via the explicit human-action path -> the next
    otherwise-approvable signal is accepted again, and exactly one
    kill_switch_released AuditEvent exists with a non-null actor.
    """
    engine, kill_switch, broker, portfolio, config, _, _, t1 = _setup_one_open_position_one_pending(
        tmp_path / "db4.db", T0
    )
    kill_switch.engage("global", "manual_drill", actor="owner", now=t1)
    kill_switch.release("global", actor="owner", now=t1)

    release_events = broker.audit.events(event_type="kill_switch_released")
    assert len(release_events) == 1
    assert release_events[0]["actor"] == "owner"

    resumed = _signal("after-release", t1)
    decision = engine.check(resumed, portfolio, None, config, sleeve="india_equity", now=t1)
    assert decision.allowed is True


def test_kill_release_requires_explicit_action_never_implicit(tmp_path) -> None:
    """I10: time passing, a restart, and a mode change must never, by
    themselves, flip `engaged` back to False -- only an explicit
    KillSwitch.release() call does.
    """
    db_path = tmp_path / "db5.db"
    engine, kill_switch, broker, portfolio, config, _, _, t1 = _setup_one_open_position_one_pending(
        db_path, T0
    )
    kill_switch.engage("global", "manual_drill", actor="owner", now=t1)

    # Time passing (a session boundary) does not release it.
    t2 = t1 + timedelta(days=1)
    assert kill_switch.is_engaged("global") is True

    # A restart does not release it.
    engine2, kill_switch2, broker2, portfolio2, config2 = _rig(db_path)
    assert kill_switch2.is_engaged("global") is True

    # A mode change (ModeGate consulted with a different sleeve_mode) does
    # not release it -- the kill switch is orthogonal to sleeve mode.
    decision = engine2.check(
        _signal("still-blocked", t2), portfolio2, None, config2, sleeve="india_equity", now=t2
    )
    assert decision.allowed is False
    for mode in (Mode.PAPER, Mode.APPROVAL, Mode.AUTO):
        assert (
            ModeGate.route(decision, mode, "approve") == Route.NONE
        )  # rejected decision, any mode

    assert kill_switch2.is_engaged("global") is True


def test_kill_drill_survives_restart_between_engage_and_check(tmp_path) -> None:
    """Step 6, I12: restart between engagement and the next check -- the
    engagement must still block new entries without re-engaging in the test.
    """
    db_path = tmp_path / "db6.db"
    _, kill_switch, _, _, _, _, _, t1 = _setup_one_open_position_one_pending(db_path, T0)
    kill_switch.engage("global", "manual_drill", actor="owner", now=t1)

    engine2, kill_switch2, broker2, portfolio2, config2 = _rig(db_path)
    assert kill_switch2.is_engaged("global") is True
    decision = engine2.check(
        _signal("post-restart", t1), portfolio2, None, config2, sleeve="india_equity", now=t1
    )
    assert decision.allowed is False
    assert decision.reason_codes == (ReasonCode.KILL_SWITCH_ENGAGED,)


def test_kill_drill_restart_reconciles_pending_fill_not_silently(tmp_path) -> None:
    """I12, ties PAPER_BROKER_SPEC.md §4's dual-read: engage the kill switch
    while a signal is still sitting in pending_fills, restart, then feed the
    fill candle -- the order resolves to exactly one terminal outcome, never
    zero (dropped by a bad restart) and never two (duplicated by one).
    """
    db_path = tmp_path / "db7.db"
    _, kill_switch, _, _, _, _, pending_signal, t1 = _setup_one_open_position_one_pending(
        db_path, T0
    )
    kill_switch.engage("global", "manual_drill", actor="owner", now=t1)

    engine2, kill_switch2, broker2, portfolio2, config2 = _rig(db_path)
    assert len(broker2.pending_signals()) == 1  # reconstructed, not dropped

    t2 = t1 + timedelta(days=1)
    broker2.on_candle(
        market=MKT,
        symbol="ICICIBANK",
        ts_open_utc=t2,
        open_=Decimal(2490),
        high=Decimal(2495),
        low=Decimal(2485),
        now=t2,
    )
    assert broker2.pending_signals() == []
    fills_for_signal = broker2._conn.execute(
        "SELECT COUNT(*) FROM fills WHERE order_id = ?", (pending_signal.id,)
    ).fetchone()[0]
    assert fills_for_signal == 1  # exactly one, never zero, never two


def test_kill_automatic_trigger_matches_manual_path(tmp_path) -> None:
    """Step 2's automatic branch: drive max_daily_loss_pct/drawdown past its
    threshold via a fixture, not a manual engage() call -- the resulting
    kill_switch_state row and AuditEvent are indistinguishable in shape from
    the manual path except reason/actor (actor="system" vs. a human id).

    RISK_ENGINE_SPEC.md §8: `check()` stays read-only/pure on a drawdown
    breach; the actual engagement is the separate `monitor_portfolio()`
    path, called here explicitly -- matching how a real caller would invoke
    it after each fill/mark, not folded into `check()` itself.
    """
    db_path = tmp_path / "auto.db"
    engine, kill_switch, broker, portfolio, config = _rig(db_path)
    from dataclasses import replace

    breached = replace(
        portfolio, portfolio_peak_equity=Decimal(1_000_000), portfolio_equity=Decimal(850_000)
    )
    d = engine.check(_signal("drawdown", T0), breached, None, config, sleeve="india_equity", now=T0)
    assert d.allowed is False
    assert d.reason_codes == (ReasonCode.PORTFOLIO_DRAWDOWN_KILL,)
    assert kill_switch.is_engaged("global") is False  # check() alone never engages it

    assert engine.monitor_portfolio(breached, config, now=T0) is True
    assert kill_switch.is_engaged("global") is True

    automatic_events = broker.audit.events(event_type="kill_switch_engaged")
    assert len(automatic_events) == 1
    row = automatic_events[0]
    assert row["actor"] == "system"  # vs. a human identifier on the manual path

    # Manual path, for shape comparison -- same event_type, same payload keys.
    kill_switch.engage("sleeve:india_equity", "manual_drill", actor="owner", now=T0)
    manual_events = broker.audit.events(event_type="kill_switch_engaged")
    manual_row = [r for r in manual_events if r["actor"] == "owner"][0]
    assert set(json.loads(row["payload_json"]).keys()) == set(
        json.loads(manual_row["payload_json"]).keys()
    )
