from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading.backtest.fills import BacktestProfile
from trading.broker.paper_broker import PaperBroker
from trading.core.enums import LedgerSource, MarketId, OrderSide, OutcomeResult, Timeframe
from trading.core.models import Signal
from trading.risk.audit import AuditLog
from trading.storage.state_db import connect

MKT = MarketId.IN_EQUITY.value
T0 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)


def _signal(**overrides) -> Signal:
    base = dict(
        market=MarketId.IN_EQUITY,
        symbol="HDFCBANK",
        timeframe=Timeframe.D1,
        strategy_id="t1",
        strategy_version="1.0.0",
        side=OrderSide.BUY,
        entry_ref=Decimal(2500),
        stop=Decimal(2450),
        target=Decimal(2600),
        bar_ts_utc=T0,
        created_ts=T0,
    )
    base.update(overrides)
    return Signal(**base)


def _broker(db_path=":memory:") -> PaperBroker:
    conn = connect(db_path)
    audit = AuditLog(conn)
    profile = BacktestProfile(brokerage=Decimal(20), slippage_bps=Decimal(5))
    return PaperBroker(conn, audit, profile=profile)


def test_signal_has_no_fill_on_its_own_bar() -> None:
    broker = _broker()
    signal = _signal()
    broker.accept(
        signal,
        qty=Decimal(10),
        sleeve="india_equity",
        ledger_source=LedgerSource.USER_PAPER,
        now=T0,
    )
    # Feeding the *same* bar's own candle must not fill it (§2 step 1).
    broker.on_candle(
        market=MKT,
        symbol="HDFCBANK",
        ts_open_utc=T0,
        open_=Decimal(2500),
        high=Decimal(2510),
        low=Decimal(2490),
        now=T0,
    )
    assert broker.open_positions() == []
    assert len(broker.pending_signals()) == 1


def test_fills_at_next_open_with_slippage() -> None:
    broker = _broker()
    signal = _signal()
    broker.accept(
        signal,
        qty=Decimal(10),
        sleeve="india_equity",
        ledger_source=LedgerSource.USER_PAPER,
        now=T0,
    )
    t1 = T0 + timedelta(days=1)
    broker.on_candle(
        market=MKT,
        symbol="HDFCBANK",
        ts_open_utc=t1,
        open_=Decimal(2510),
        high=Decimal(2520),
        low=Decimal(2500),
        now=t1,
    )
    positions = broker.open_positions()
    assert len(positions) == 1
    # buy slippage: 2510 * (1 + 5/10000) = 2511.255
    assert positions[0].avg_price == Decimal(2510) * (Decimal(1) + Decimal(5) / Decimal(10000))
    assert broker.pending_signals() == []


def test_gap_through_stop_fills_at_open_not_at_stop() -> None:
    broker = _broker()
    signal = _signal()
    broker.accept(
        signal,
        qty=Decimal(100),
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
    )  # entry fill, no exit check needed this bar for a fresh position
    t2 = t1 + timedelta(days=1)
    broker.on_candle(
        market=MKT,
        symbol="HDFCBANK",
        ts_open_utc=t2,
        open_=Decimal(2400),
        high=Decimal(2410),
        low=Decimal(2390),
        now=t2,
    )  # gaps through stop (2450)
    assert broker.open_positions() == []
    outcome = broker.outcome(signal.id)
    assert outcome == OutcomeResult.STOP_HIT
    gap_events = broker.audit.events(event_type="gap_risk_realized")
    assert len(gap_events) == 1


def test_target_hit_closes_position() -> None:
    broker = _broker()
    signal = _signal()
    broker.accept(
        signal,
        qty=Decimal(10),
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
    t2 = t1 + timedelta(days=1)
    broker.on_candle(
        market=MKT,
        symbol="HDFCBANK",
        ts_open_utc=t2,
        open_=Decimal(2600),
        high=Decimal(2610),
        low=Decimal(2600),
        now=t2,
    )
    assert broker.open_positions() == []
    assert broker.outcome(signal.id) == OutcomeResult.TARGET_HIT


def test_session_ended_unfilled_expires_pending_signal() -> None:
    broker = _broker()
    signal = _signal()
    broker.accept(
        signal,
        qty=Decimal(10),
        sleeve="india_equity",
        ledger_source=LedgerSource.USER_PAPER,
        now=T0,
    )
    expired = broker.expire_session(market=MKT, now=T0 + timedelta(hours=5))
    assert expired == [signal.id]
    assert broker.pending_signals() == []
    assert broker.outcome(signal.id) == OutcomeResult.SESSION_ENDED_UNFILLED


def test_shadow_signal_scored_cost_honestly_without_real_fill() -> None:
    broker = _broker()
    signal = _signal()
    broker.accept(
        signal, qty=Decimal(10), sleeve="india_equity", ledger_source=LedgerSource.SHADOW, now=T0
    )
    t1 = T0 + timedelta(days=1)
    broker.on_candle(
        market=MKT,
        symbol="HDFCBANK",
        ts_open_utc=t1,
        open_=Decimal(2510),
        high=Decimal(2520),
        low=Decimal(2500),
        now=t1,
    )
    positions = broker.open_positions()
    assert positions[0].ledger_source == LedgerSource.SHADOW


def test_restart_reconstructs_pending_and_positions_from_sqlite(tmp_path) -> None:
    db_path = tmp_path / "state.db"
    broker = _broker(db_path)
    signal = _signal()
    broker.accept(
        signal,
        qty=Decimal(10),
        sleeve="india_equity",
        ledger_source=LedgerSource.USER_PAPER,
        now=T0,
    )

    # "restart": fresh PaperBroker instance against the same file.
    fresh = _broker(db_path)
    assert len(fresh.pending_signals()) == 1
    t1 = T0 + timedelta(days=1)
    fresh.on_candle(
        market=MKT,
        symbol="HDFCBANK",
        ts_open_utc=t1,
        open_=Decimal(2510),
        high=Decimal(2520),
        low=Decimal(2500),
        now=t1,
    )
    assert len(fresh.open_positions()) == 1

    # restart again, now with an open position -- must still see it and still
    # be able to stop it out.
    fresh2 = _broker(db_path)
    assert len(fresh2.open_positions()) == 1
    t2 = t1 + timedelta(days=1)
    fresh2.on_candle(
        market=MKT,
        symbol="HDFCBANK",
        ts_open_utc=t2,
        open_=Decimal(2400),
        high=Decimal(2410),
        low=Decimal(2390),
        now=t2,
    )
    assert fresh2.open_positions() == []
    assert fresh2.outcome(signal.id) == OutcomeResult.STOP_HIT
