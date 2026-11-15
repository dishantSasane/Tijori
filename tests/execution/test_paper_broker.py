from __future__ import annotations

from decimal import Decimal

import pytest

from tests.execution.conftest import make_candle, make_decision, make_signal
from trading.backtest.fills import BacktestProfile
from trading.execution.paper_broker import PaperBroker, PaperBrokerHaltedError


def test_submit_entry_then_fill_at_next_open(store, kill_switch, clock):
    broker = PaperBroker(store, kill_switch, clock=clock)
    assert broker.is_paper()
    signal = make_signal()
    decision = make_decision(signal)
    order = broker.submit_entry(
        signal,
        decision,
        profile=BacktestProfile(brokerage=Decimal("10"), slippage_bps=Decimal("5")),
    )
    assert order.status.value == "risk_approved"
    assert store.pending_fill_ids() == [signal.id]

    candle = make_candle(Decimal("2501"), Decimal("2550"), Decimal("2490"), Decimal("2520"))
    broker.on_closed_candle(candle)

    assert store.pending_fill_ids() == []
    positions = store.positions()
    assert len(positions) == 1
    assert Decimal(positions[0]["qty"]) == Decimal(100)
    # buy slips adverse (up): 2501 * 1.0005
    assert Decimal(positions[0]["avg_price"]) == Decimal("2501") * Decimal("1.0005")


def test_i1_never_calls_a_real_broker():
    """PaperBroker has no attribute/path to a real broker adapter at all."""
    import inspect

    import trading.execution.paper_broker as mod

    source = inspect.getsource(mod)
    for forbidden in ("kiteconnect", "alpaca", "ccxt"):
        assert forbidden not in source.lower()


def test_submit_entry_rejects_disallowed_decision(store, kill_switch, clock):
    from trading.core.enums import ReasonCode
    from trading.core.models import RiskDecision

    broker = PaperBroker(store, kill_switch, clock=clock)
    signal = make_signal()
    rejected = RiskDecision(
        signal_id=signal.id,
        allowed=False,
        qty=Decimal(0),
        reason_codes=(ReasonCode.MARKET_CLOSED,),
        created_ts=clock.now(),
    )
    with pytest.raises(ValueError):
        broker.submit_entry(signal, rejected, profile=BacktestProfile())


def test_kill_switch_blocks_new_entries(store, kill_switch, clock):
    from trading.risk.kill_switch import GLOBAL_SCOPE

    broker = PaperBroker(store, kill_switch, clock=clock)
    kill_switch.engage(GLOBAL_SCOPE, "drill")
    signal = make_signal()
    decision = make_decision(signal)
    with pytest.raises(PaperBrokerHaltedError):
        broker.submit_entry(signal, decision, profile=BacktestProfile())


def test_gap_through_stop_emits_gap_risk_event(store, kill_switch, clock):
    broker = PaperBroker(store, kill_switch, clock=clock)
    signal = make_signal(entry_ref=Decimal(2500), stop=Decimal(2450))
    decision = make_decision(signal)
    broker.submit_entry(signal, decision, profile=BacktestProfile())
    broker.on_closed_candle(make_candle(Decimal(2500), Decimal(2500), Decimal(2500), Decimal(2500)))

    # Next candle gaps straight through the stop.
    broker.on_closed_candle(make_candle(Decimal(2400), Decimal(2410), Decimal(2390), Decimal(2395)))
    events = store.audit_events("gap_risk_realized")
    assert len(events) == 1
    assert events[0]["payload"]["approved_risk"] == "5000"
    assert events[0]["payload"]["realized_risk"] == "10000"
    assert store.positions() == []
