"""The automated form of docs/specs/PAPER_BROKER_SPEC.md §6's 6-step drill,
per docs/specs/TEST_SPEC_RISK.md §8. Exercises the real PaperBroker (not
FakePaperBroker) against SQLite so persistence/restart are genuinely tested.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading.backtest.fills import BacktestProfile
from trading.broker.paper_broker import PaperBroker
from trading.core.enums import (
    LedgerSource,
    MarketId,
    OrderSide,
    OutcomeResult,
    ReasonCode,
    Timeframe,
)
from trading.core.models import Signal
from trading.risk.audit import AuditLog
from trading.risk.decision_store import DecisionStore
from trading.risk.engine import RiskEngine
from trading.risk.fakes import FakeDataFreshness, FakeSessionCalendar
from trading.risk.kill_switch import KillSwitch
from trading.risk.portfolio import PortfolioState, RiskConfig, SleeveState
from trading.storage.state_db import connect

MKT = MarketId.IN_EQUITY.value
T0 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)


def _signal(signal_id_suffix: str, bar_ts) -> Signal:
    return Signal(
        id=f"sig-{signal_id_suffix}",
        market=MarketId.IN_EQUITY,
        symbol="HDFCBANK",
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


def test_automatic_trigger_matches_manual_path_in_shape(tmp_path) -> None:
    db_path = tmp_path / "auto.db"
    engine, kill_switch, broker, portfolio, config = _rig(db_path)
    from dataclasses import replace

    # Drive drawdown past the configured threshold -- a fixture, not a manual
    # engage() call -- and let check() itself trigger the engagement (§8).
    breached = replace(
        portfolio, portfolio_peak_equity=Decimal(1_000_000), portfolio_equity=Decimal(850_000)
    )
    d = engine.check(_signal("drawdown", T0), breached, None, config, sleeve="india_equity", now=T0)
    assert d.allowed is False
    assert d.reason_codes == (ReasonCode.PORTFOLIO_DRAWDOWN_KILL,)
    assert kill_switch.is_engaged("global") is True

    manual_events = [e for e in broker.audit.events(event_type="kill_switch_engaged")]
    assert len(manual_events) == 1
    row = manual_events[0]
    assert row["actor"] == "system"  # vs. a human identifier on the manual path
