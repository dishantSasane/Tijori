from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trading.core.enums import MarketId, OrderSide, Timeframe
from trading.core.models import Signal
from trading.risk.audit import AuditLog
from trading.risk.decision_store import DecisionStore
from trading.risk.engine import RiskEngine
from trading.risk.fakes import FakeDataFreshness, FakeSessionCalendar
from trading.risk.kill_switch import KillSwitch
from trading.risk.portfolio import PortfolioState, RiskConfig, SleeveState
from trading.storage.state_db import connect

TS = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)


@pytest.fixture
def conn():
    return connect(":memory:")


@pytest.fixture
def audit(conn):
    return AuditLog(conn)


@pytest.fixture
def engine(conn, audit):
    calendar = FakeSessionCalendar(open_markets={MarketId.IN_EQUITY.value})
    freshness = FakeDataFreshness()
    kill_switch = KillSwitch(conn, audit)
    decisions = DecisionStore(conn)
    e = RiskEngine(
        kill_switch=kill_switch, decision_store=decisions, calendar=calendar, freshness=freshness
    )
    e.calendar = calendar  # test-only handle
    e.freshness = freshness
    e.kill_switch_handle = kill_switch
    return e


@pytest.fixture
def passing_signal() -> Signal:
    return Signal(
        market=MarketId.IN_EQUITY,
        symbol="HDFCBANK",
        timeframe=Timeframe.D1,
        strategy_id="t1",
        strategy_version="1.0.0",
        side=OrderSide.BUY,
        entry_ref=Decimal(2500),
        stop=Decimal(2450),
        bar_ts_utc=TS,
        created_ts=TS,
    )


@pytest.fixture
def passing_portfolio() -> PortfolioState:
    sleeve = SleeveState(
        equity=Decimal(1_000_000),
        open_positions=0,
        daily_pnl_pct=Decimal(0),
        allocation_used_pct=Decimal(10),
        allocation_cap_pct=Decimal(40),
        max_positions=6,
    )
    return PortfolioState(
        sleeves={"india_equity": sleeve},
        total_open_positions=0,
        portfolio_peak_equity=Decimal(1_000_000),
        portfolio_equity=Decimal(1_000_000),
    )


@pytest.fixture
def passing_config() -> RiskConfig:
    return RiskConfig(
        market=MarketId.IN_EQUITY,
        risk_per_trade_pct=Decimal("0.5"),
        max_position_value_pct=Decimal(100),
        max_risk_distance_pct_of_entry=Decimal(10),
        order_price_band_pct=Decimal(5),
        stale_data_seconds=30,
        max_portfolio_drawdown_pct=Decimal(10),
        max_daily_loss_pct=Decimal(2),
    )
