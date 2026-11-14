from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from trading.core.enums import (
    BrainLabel,
    MarketId,
    OrderSide,
    OrderStatus,
    ReasonCode,
    Timeframe,
)
from trading.core.models import Candle, Order, RiskDecision, Signal

UTC_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_candle_rejects_high_below_low() -> None:
    with pytest.raises(ValidationError, match="high < low"):
        Candle(
            market=MarketId.IN_EQUITY,
            symbol="RELIANCE",
            timeframe=Timeframe.D1,
            ts_open_utc=UTC_NOW,
            open=Decimal(10),
            high=Decimal(5),
            low=Decimal(8),
            close=Decimal(9),
            volume=Decimal(100),
            source="test",
            ingest_ts=UTC_NOW,
        )


def test_candle_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        Candle(
            market=MarketId.IN_EQUITY,
            symbol="RELIANCE",
            timeframe=Timeframe.D1,
            ts_open_utc=datetime(2026, 1, 1),
            open=Decimal(10),
            high=Decimal(11),
            low=Decimal(9),
            close=Decimal(10),
            volume=Decimal(100),
            source="test",
            ingest_ts=UTC_NOW,
        )


def test_candle_rejects_non_utc_offset() -> None:
    ist = timezone(timedelta(hours=5, minutes=30))
    with pytest.raises(ValidationError, match="must be UTC"):
        Candle(
            market=MarketId.IN_EQUITY,
            symbol="RELIANCE",
            timeframe=Timeframe.D1,
            ts_open_utc=datetime(2026, 1, 1, tzinfo=ist),
            open=Decimal(10),
            high=Decimal(11),
            low=Decimal(9),
            close=Decimal(10),
            volume=Decimal(100),
            source="test",
            ingest_ts=UTC_NOW,
        )


def test_candle_is_immutable() -> None:
    candle = Candle(
        market=MarketId.IN_EQUITY,
        symbol="RELIANCE",
        timeframe=Timeframe.D1,
        ts_open_utc=UTC_NOW,
        open=Decimal(10),
        high=Decimal(11),
        low=Decimal(9),
        close=Decimal(10),
        volume=Decimal(100),
        source="test",
        ingest_ts=UTC_NOW,
    )
    with pytest.raises(ValidationError):
        candle.close = Decimal(20)  # type: ignore[misc]


def test_buy_signal_requires_stop_below_entry() -> None:
    with pytest.raises(ValidationError, match="below entry_ref"):
        Signal(
            market=MarketId.IN_EQUITY,
            symbol="RELIANCE",
            timeframe=Timeframe.D1,
            strategy_id="t1_donchian",
            strategy_version="v1",
            side=OrderSide.BUY,
            entry_ref=Decimal(100),
            stop=Decimal(105),
            bar_ts_utc=UTC_NOW,
            created_ts=UTC_NOW,
        )


def test_sell_signal_requires_stop_above_entry() -> None:
    with pytest.raises(ValidationError, match="above entry_ref"):
        Signal(
            market=MarketId.IN_EQUITY,
            symbol="RELIANCE",
            timeframe=Timeframe.D1,
            strategy_id="t1_donchian",
            strategy_version="v1",
            side=OrderSide.SELL,
            entry_ref=Decimal(100),
            stop=Decimal(95),
            bar_ts_utc=UTC_NOW,
            created_ts=UTC_NOW,
        )


def test_signal_without_stop_is_constructible_but_unapproved_downstream() -> None:
    # A missing stop is a risk-engine rejection (ReasonCode.SIGNAL_MISSING_STOP),
    # not a contract-level error, so the rejection is auditable.
    signal = Signal(
        market=MarketId.IN_EQUITY,
        symbol="RELIANCE",
        timeframe=Timeframe.D1,
        strategy_id="t1_donchian",
        strategy_version="v1",
        side=OrderSide.BUY,
        entry_ref=Decimal(100),
        stop=None,
        bar_ts_utc=UTC_NOW,
        created_ts=UTC_NOW,
    )
    assert signal.stop is None


def test_order_qty_filled_cannot_exceed_qty() -> None:
    with pytest.raises(ValidationError, match="invariant I3"):
        Order(
            request_id="req-1",
            status=OrderStatus.PARTIALLY_FILLED,
            qty=Decimal(10),
            qty_filled=Decimal(11),
            created_ts=UTC_NOW,
            updated_ts=UTC_NOW,
        )


def test_risk_decision_allowed_requires_positive_qty() -> None:
    with pytest.raises(ValidationError, match="invariant I9"):
        RiskDecision(
            signal_id="sig-1",
            allowed=True,
            qty=Decimal(0),
            reason_codes=(ReasonCode.OK,),
            created_ts=UTC_NOW,
        )


def test_risk_decision_rejected_requires_zero_qty() -> None:
    with pytest.raises(ValidationError, match="qty == 0"):
        RiskDecision(
            signal_id="sig-1",
            allowed=False,
            qty=Decimal(5),
            reason_codes=(ReasonCode.KILL_SWITCH_ENGAGED,),
            created_ts=UTC_NOW,
        )


def test_risk_decision_requires_at_least_one_reason_code() -> None:
    with pytest.raises(ValidationError):
        RiskDecision(
            signal_id="sig-1",
            allowed=False,
            qty=Decimal(0),
            reason_codes=(),
            created_ts=UTC_NOW,
        )


def test_brain_verdict_size_multiplier_bounds() -> None:
    from trading.core.models import BrainVerdict

    with pytest.raises(ValidationError):
        BrainVerdict(
            signal_id="sig-1",
            label=BrainLabel.SUPPORT,
            size_multiplier=Decimal("1.5"),
            created_ts=UTC_NOW,
        )
