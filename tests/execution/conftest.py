from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trading.core.clock import FixedClock
from trading.core.enums import MarketId, OrderSide, Timeframe
from trading.core.models import Candle, RiskDecision, Signal
from trading.risk.kill_switch import KillSwitch
from trading.storage.state_store import StateStore

NOW = datetime(2026, 1, 5, 5, 0, tzinfo=UTC)


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(at=NOW)


@pytest.fixture
def store(tmp_path):
    s = StateStore(tmp_path / "paper.db")
    yield s
    s.close()


@pytest.fixture
def kill_switch(store, clock) -> KillSwitch:
    return KillSwitch(store, clock=clock)


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
        bar_ts_utc=NOW,
        created_ts=NOW,
    )
    defaults.update(overrides)
    return Signal(**defaults)


def make_decision(signal: Signal, qty: Decimal = Decimal(100)) -> RiskDecision:
    from trading.core.enums import ReasonCode

    return RiskDecision(
        signal_id=signal.id, allowed=True, qty=qty, reason_codes=(ReasonCode.OK,), created_ts=NOW
    )


def make_candle(
    open_price: Decimal,
    high: Decimal,
    low: Decimal,
    close: Decimal,
    *,
    market=MarketId.IN_EQUITY,
    symbol="RELIANCE",
) -> Candle:
    return Candle(
        market=market,
        symbol=symbol,
        timeframe=Timeframe.D1,
        ts_open_utc=NOW,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=Decimal(1000),
        source="test",
        ingest_ts=NOW,
    )
