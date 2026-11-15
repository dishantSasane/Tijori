from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading.backtest.daily_candidates import run_p1_daily_candidate
from trading.backtest.fills import BacktestProfile
from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle


def test_frozen_daily_candidate_runs_through_shared_fill_and_position_engine() -> None:
    start = datetime(2020, 1, 1, tzinfo=UTC)
    candles = [
        Candle(
            market=MarketId.IN_EQUITY,
            symbol="TEST",
            timeframe=Timeframe.D1,
            ts_open_utc=start + timedelta(days=index),
            open=Decimal(100 + index * 2),
            high=Decimal(101 + index * 2),
            low=Decimal(99 + index * 2),
            close=Decimal(100 + index * 2),
            volume=Decimal("1000"),
            source="test",
            ingest_ts=start,
        )
        for index in range(45)
    ]

    result = run_p1_daily_candidate(
        "t1-donchian-n20-m10-k2-v1",
        candles,
        created_ts=start,
        quantity=Decimal("1"),
        profile=BacktestProfile(),
    )

    assert result.trades == []
    assert result.open_positions == 1
    assert result.open_trades[0].entry_bar == 21
    assert result.open_trades[0].entry_price == Decimal("142")
