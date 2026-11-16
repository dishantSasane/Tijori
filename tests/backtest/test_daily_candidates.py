from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from trading.backtest.daily_candidates import run_p1_daily_candidate
from trading.backtest.fills import BacktestProfile
from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle
from trading.storage.action_register import ActionRegister, CoverageRecord


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


def test_real_sourced_candles_fail_closed_without_a_register() -> None:
    """Regression for the gap note 0045 fixes: `run_p1_daily_candidate` used
    to drop action_register/candle_snapshot_sha256/reviewed_action_keys
    entirely, so real (non-"test") candles had no way to ever supply a
    reviewed register and could only fail. They must still fail closed by
    default -- this proves the parameters now reach `action_preflight` at
    all, by observing the specific "register is required" error instead of
    some other failure.
    """
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
            source="upstox",  # real source, not "test"
            ingest_ts=start,
        )
        for index in range(45)
    ]
    with pytest.raises(ValueError, match="reviewed corporate-action register is required"):
        run_p1_daily_candidate(
            "t1-donchian-n20-m10-k2-v1",
            candles,
            created_ts=start,
            quantity=Decimal("1"),
            profile=BacktestProfile(),
        )


def test_real_sourced_candles_pass_closed_with_a_covering_register() -> None:
    """Same candles as above, but now a verified covering register is
    supplied -- proves the parameters are not just accepted but actually
    threaded through to `run_long_only`'s preflight, not silently dropped.
    """
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
            source="upstox",
            ingest_ts=start,
        )
        for index in range(45)
    ]
    snapshot_sha = "b" * 64
    register = ActionRegister(
        coverage=(
            CoverageRecord(
                symbol="RELIANCE",
                timeframe=Timeframe.D1,
                candle_snapshot_sha256=snapshot_sha,
                isin="INE002A01018",
                start=date(2020, 1, 1),
                end=date(2020, 2, 14),
                verified=True,
                source_url="https://example.test/coverage",
                reviewer="fixture-reviewer",
                review_date=date(2020, 2, 15),
            ),
        )
    )
    candles = [c.model_copy(update={"symbol": "RELIANCE"}) for c in candles]

    result = run_p1_daily_candidate(
        "t1-donchian-n20-m10-k2-v1",
        candles,
        created_ts=start,
        quantity=Decimal("1"),
        profile=BacktestProfile(),
        action_register=register,
        candle_snapshot_sha256=snapshot_sha,
    )
    assert result.action_review_flags == ()


def test_daily_candidate_condition_exit_uses_open_and_configured_exit_fee() -> None:
    start = datetime(2020, 1, 1, tzinfo=UTC)
    closes = [100] * 205 + [120] * 10 + [115, 110, 130, 100]
    candles = []
    for index, close in enumerate(closes):
        open_price = close
        high = close + 1
        low = close - 1
        if index == 217:
            open_price, high, low = 112, 131, 111
        elif index == 218:
            open_price, high, low = 110, 110, 90
        candles.append(
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
                source="test",
                ingest_ts=start,
            )
        )

    result = run_p1_daily_candidate(
        "t4-rsi2-10-atr25-v1",
        candles,
        created_ts=start,
        quantity=Decimal("1"),
        profile=BacktestProfile(
            brokerage=Decimal("1"),
            entry_brokerage=Decimal("2"),
            exit_brokerage=Decimal("7"),
        ),
    )

    assert len(result.trades) == 1
    assert result.trades[0].exit_reason == "condition"
    assert result.trades[0].exit_price == Decimal("110")
    assert result.trades[0].fees == Decimal("9")
