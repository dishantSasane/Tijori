"""Covers docs/specs/PAPER_BROKER_SPEC.md §4's dual-read: positions table vs.
an independent replay of audit_log.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading.backtest.fills import BacktestProfile
from trading.broker.paper_broker import PaperBroker
from trading.broker.reconciliation import ReconciliationError, reconcile
from trading.core.enums import LedgerSource, MarketId, OrderSide, Timeframe
from trading.core.models import Signal
from trading.risk.audit import AuditLog
from trading.storage.state_db import connect

MKT = MarketId.IN_EQUITY.value
T0 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)


def _signal() -> Signal:
    return Signal(
        market=MarketId.IN_EQUITY,
        symbol="HDFCBANK",
        timeframe=Timeframe.D1,
        strategy_id="t1",
        strategy_version="1.0.0",
        side=OrderSide.BUY,
        entry_ref=Decimal(2500),
        stop=Decimal(2450),
        bar_ts_utc=T0,
        created_ts=T0,
    )


def _broker():
    conn = connect(":memory:")
    audit = AuditLog(conn)
    profile = BacktestProfile(brokerage=Decimal(0), slippage_bps=Decimal(0))
    return conn, PaperBroker(conn, audit, profile=profile)


def test_reconciliation_ok_with_no_positions() -> None:
    conn, _broker_instance = _broker()
    result = reconcile(conn)
    assert result.ok is True
    assert result.mismatches == ()


def test_reconciliation_ok_after_a_real_entry_fill() -> None:
    conn, broker = _broker()
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
    result = reconcile(conn)
    assert result.ok is True


def test_reconciliation_ok_after_a_full_close() -> None:
    conn, broker = _broker()
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
    )
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
    result = reconcile(conn)
    assert result.ok is True


def test_reconciliation_detects_a_phantom_position_not_backed_by_audit_log() -> None:
    """Deliberate mismatch: a position row exists with no corresponding
    entry_filled audit event -- as if something wrote to `positions`
    without going through the audited fill path.
    """
    conn, _broker_instance = _broker()
    conn.execute(
        "INSERT INTO positions (market, symbol, sleeve, signal_id, qty, avg_price, opened_ts, "
        "stop_price, target_price, entry_ref, approved_risk, ledger_source) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            MKT,
            "HDFCBANK",
            "india_equity",
            "phantom-signal",
            "50",
            "2500",
            T0.isoformat(),
            "2450",
            None,
            "2500",
            "2500",
            "user_paper",
        ),
    )
    conn.commit()

    result = reconcile(conn)
    assert result.ok is False
    assert len(result.mismatches) == 1
    mismatch = result.mismatches[0]
    assert mismatch.position_key == f"{MKT}:HDFCBANK:india_equity"
    assert mismatch.expected_qty is None  # audit_log says this position shouldn't exist
    assert mismatch.actual_qty == Decimal(50)


def test_reconciliation_detects_a_quantity_drift() -> None:
    """Deliberate mismatch: the entry filled for qty=10 (per audit_log), but
    the positions row was somehow corrupted to a different quantity.
    """
    conn, broker = _broker()
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
    assert reconcile(conn).ok is True

    conn.execute(
        "UPDATE positions SET qty = '999' WHERE market = ? AND symbol = ? AND sleeve = ?",
        (MKT, "HDFCBANK", "india_equity"),
    )
    conn.commit()

    result = reconcile(conn)
    assert result.ok is False
    mismatch = result.mismatches[0]
    assert mismatch.expected_qty == Decimal(10)
    assert mismatch.actual_qty == Decimal(999)


def test_reconciliation_detects_a_missing_position_audit_says_should_exist() -> None:
    """Deliberate mismatch: audit_log recorded a fill, but the positions row
    was dropped (e.g. an incomplete restart or a bad delete).
    """
    conn, broker = _broker()
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

    conn.execute("DELETE FROM positions WHERE market = ? AND symbol = ?", (MKT, "HDFCBANK"))
    conn.commit()

    result = reconcile(conn)
    assert result.ok is False
    mismatch = result.mismatches[0]
    assert mismatch.expected_qty == Decimal(10)
    assert mismatch.actual_qty is None


def test_raise_if_inconsistent_only_raises_on_mismatch() -> None:
    conn, broker = _broker()
    reconcile(conn).raise_if_inconsistent()  # no positions yet -- must not raise

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
    reconcile(conn).raise_if_inconsistent()  # consistent -- must not raise

    conn.execute(
        "UPDATE positions SET qty = '999' WHERE market = ? AND symbol = ? AND sleeve = ?",
        (MKT, "HDFCBANK", "india_equity"),
    )
    conn.commit()
    try:
        reconcile(conn).raise_if_inconsistent()
        raise AssertionError("expected ReconciliationError")
    except ReconciliationError as exc:
        assert "HDFCBANK" in str(exc)
