from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading.backtest.fills import BacktestProfile
from trading.backtest.reference import run_reference
from trading.core.enums import MarketId, OrderSide, Timeframe
from trading.core.models import Candle, Signal


def bar(index: int, open_price: str, high: str, low: str, close: str) -> Candle:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=index)
    return Candle(
        market=MarketId.IN_EQUITY,
        symbol="TEST",
        timeframe=Timeframe.D1,
        ts_open_utc=timestamp,
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("1000"),
        source="test",
        ingest_ts=timestamp,
    )


def signal(index: int) -> Signal:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=index)
    return Signal(
        market=MarketId.IN_EQUITY,
        symbol="TEST",
        timeframe=Timeframe.D1,
        strategy_id="test",
        strategy_version="1.0.0",
        side=OrderSide.BUY,
        entry_ref=Decimal("2500"),
        stop=Decimal("2450"),
        bar_ts_utc=timestamp,
        created_ts=timestamp,
    )


def test_reference_records_overnight_gap_with_nonzero_slippage() -> None:
    candles = [
        bar(0, "2500", "2510", "2490", "2500"),
        bar(1, "2500", "2510", "2490", "2500"),
        bar(2, "2400", "2420", "2390", "2410"),
    ]
    entry = signal(0).model_copy(update={"entry_ref": Decimal("2500"), "stop": Decimal("2450")})
    result = run_reference(
        candles,
        [entry],
        quantity=Decimal("100"),
        profile=BacktestProfile(slippage_bps=Decimal("5")),
    )
    assert result.audit_events == ["gap_risk_realized:approved_risk=5000:realized_risk=10120.0000"]
