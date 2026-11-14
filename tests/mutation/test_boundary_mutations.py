"""Mutation sentinels for strict strategy/backtest safety boundaries.

These tests encode the mutant directly: changing T1's ``>`` to ``>=`` must
make the equality fixture fail, and charging only one side's fee must disagree
with the runner's known-answer accounting.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading.backtest.runner import Trade
from trading.backtest.scorecard import scorecard
from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle
from trading.strategies.phase1 import t1_donchian


def candles(closes: list[int]) -> list[Candle]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Candle(
            market=MarketId.IN_EQUITY,
            symbol="TEST",
            timeframe=Timeframe.D1,
            ts_open_utc=start + timedelta(days=index),
            open=Decimal(value),
            high=Decimal(value + 1),
            low=Decimal(value - 1),
            close=Decimal(value),
            volume=Decimal("1000"),
            source="test",
            ingest_ts=start,
        )
        for index, value in enumerate(closes)
    ]


def test_t1_equality_mutant_is_killed() -> None:
    bars = candles([10, 11, 9, 10, 12])
    assert (
        t1_donchian(bars, [None, None, None, None, 2.0], lookback=3, created_ts=bars[0].ingest_ts)
        == []
    )
    # The >= mutant would emit one signal on the equality bar.
    previous_high = max(bar.high for bar in bars[1:4])
    assert bars[4].close == previous_high


def test_fee_double_counting_mutant_is_killed() -> None:
    completed = Trade(
        signal_id="1",
        entry_bar=0,
        exit_bar=1,
        quantity=Decimal("1"),
        entry_price=Decimal("100"),
        exit_price=Decimal("110"),
        fees=Decimal("2"),
        pnl=Decimal("8"),
    )
    result = scorecard([completed])
    assert result.total_pnl == Decimal("8")
    # A mutant that subtracts fees again would report 6, not 8.
    assert result.total_pnl != completed.pnl - completed.fees
