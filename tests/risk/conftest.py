from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trading.core.clock import FixedClock
from trading.core.enums import MarketId, OrderSide, Timeframe
from trading.core.models import Signal
from trading.risk.config import InstanceState, PortfolioState, RiskConfig, SleeveConfig, SleeveState
from trading.risk.engine import DataFreshnessCheck, MarketSession, RiskEngine
from trading.risk.kill_switch import KillSwitch
from trading.storage.state_store import StateStore

NOW = datetime(2026, 1, 5, 5, 0, tzinfo=UTC)  # a Monday, well inside market hours


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(at=NOW)


@pytest.fixture
def store(tmp_path) -> StateStore:
    s = StateStore(tmp_path / "state.db")
    yield s
    s.close()


@pytest.fixture
def kill_switch(store, clock) -> KillSwitch:
    return KillSwitch(store, clock=clock)


@pytest.fixture
def market_open_session() -> MarketSession:
    return MarketSession(is_open=lambda signal, now: True)


@pytest.fixture
def fresh_data() -> DataFreshnessCheck:
    return DataFreshnessCheck(is_stale=lambda signal, now, max_age: False)


@pytest.fixture
def engine(kill_switch, market_open_session, fresh_data) -> RiskEngine:
    return RiskEngine(
        kill_switch=kill_switch, market_session=market_open_session, freshness=fresh_data
    )


def make_signal(**overrides) -> Signal:
    defaults = dict(
        market=MarketId.IN_EQUITY,
        symbol="RELIANCE",
        timeframe=Timeframe.D1,
        strategy_id="strat-1",
        strategy_version="v1",
        side=OrderSide.BUY,
        entry_ref=Decimal("2500"),
        stop=Decimal("2450"),
        target=Decimal("2600"),
        bar_ts_utc=NOW,
        created_ts=NOW,
    )
    defaults.update(overrides)
    return Signal(**defaults)


def make_sleeve_config(**overrides) -> SleeveConfig:
    defaults = dict(
        risk_per_trade_pct=Decimal("0.5"),
        max_position_value_pct=Decimal("50"),
        max_open_positions=10,
        sleeve_allocation_pct=Decimal("80"),
        max_daily_loss_pct=Decimal("3"),
        liquidity_cap_pct_of_adv=Decimal("1"),
        concentration_limit_pct=Decimal("5"),
        lot_size=Decimal(1),
    )
    defaults.update(overrides)
    return SleeveConfig(**defaults)


def make_config(**overrides) -> RiskConfig:
    sleeve = overrides.pop("sleeve", make_sleeve_config())
    defaults = dict(
        stale_data_seconds=30,
        order_price_band_pct=Decimal("2"),
        max_open_positions_total=20,
        max_portfolio_drawdown_pct=Decimal("20"),
        sleeve=sleeve,
    )
    defaults.update(overrides)
    return RiskConfig(**defaults)


def make_sleeve_state(**overrides) -> SleeveState:
    defaults = dict(
        equity=Decimal("1000000"),
        open_position_value=Decimal(0),
        open_position_count=0,
        daily_pnl_pct=Decimal(0),
    )
    defaults.update(overrides)
    return SleeveState(**defaults)


def make_portfolio(**overrides) -> PortfolioState:
    sleeve = overrides.pop("sleeve", make_sleeve_state())
    instance = overrides.pop("instance", InstanceState())
    defaults = dict(
        sleeve=sleeve,
        instance=instance,
        total_open_positions=0,
        portfolio_drawdown_pct=Decimal(0),
        last_tick_price=None,
        liquidity_cap_qty=Decimal(1000),
    )
    defaults.update(overrides)
    return PortfolioState(**defaults)
