from decimal import Decimal

from trading.backtest.fills import BacktestProfile
from trading.backtest.validation import validate_long_only
from trading.core.enums import MarketId, OrderSide, Timeframe
from trading.core.models import Candle, Signal


def test_validated_backtest_returns_equivalent_scorecard() -> None:
    from datetime import UTC, datetime, timedelta

    start = datetime(2026, 1, 1, tzinfo=UTC)
    bars = [
        Candle(
            market=MarketId.IN_EQUITY,
            symbol="TEST",
            timeframe=Timeframe.D1,
            ts_open_utc=start + timedelta(days=index),
            open=Decimal(open_price),
            high=Decimal(high),
            low=Decimal(low),
            close=Decimal(close),
            volume=Decimal("1000"),
            source="fixture",
            ingest_ts=start,
        )
        for index, (open_price, high, low, close) in enumerate(
            [("10", "11", "9", "10"), ("13", "14", "12", "13"), ("13", "15", "8", "12")]
        )
    ]
    signal = Signal(
        market=MarketId.IN_EQUITY,
        symbol="TEST",
        timeframe=Timeframe.D1,
        strategy_id="t1_donchian",
        strategy_version="1.0.0",
        side=OrderSide.BUY,
        entry_ref=Decimal("10"),
        stop=Decimal("9"),
        bar_ts_utc=bars[0].ts_open_utc,
        created_ts=start,
    )

    result = validate_long_only(bars, [signal], quantity=Decimal("2"), profile=BacktestProfile())

    assert result.primary == result.reference
    assert result.scorecard.trades == 1
    assert result.scorecard.total_pnl == Decimal("-8")
