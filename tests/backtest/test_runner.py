from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading.backtest.fills import BacktestProfile
from trading.backtest.runner import BacktestResult, run_long_only
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


def signal(index: int, stop: str = "9") -> Signal:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=index)
    return Signal(
        market=MarketId.IN_EQUITY,
        symbol="TEST",
        timeframe=Timeframe.D1,
        strategy_id="test",
        strategy_version="1.0.0",
        side=OrderSide.BUY,
        entry_ref=Decimal("13"),
        stop=Decimal(stop),
        bar_ts_utc=timestamp,
        created_ts=timestamp,
    )


def test_runner_fills_next_open_and_stops_first() -> None:
    candles = [
        bar(0, "10", "11", "9", "10"),
        bar(1, "13.2", "13.5", "13", "13.3"),
        bar(2, "9.5", "14", "8", "13"),
    ]
    result = run_long_only(
        candles,
        [signal(0)],
        quantity=Decimal("100"),
        profile=BacktestProfile(brokerage=Decimal("20"), slippage_bps=Decimal("5")),
    )
    assert result.trades[0].entry_price == Decimal("13.2066")
    assert result.trades[0].exit_price == Decimal("9")
    assert result.trades[0].pnl == Decimal("-440.66")


def test_final_bar_signal_is_logged_but_not_counted() -> None:
    candles = [bar(0, "10", "11", "9", "10")]
    pending = signal(0)
    result = run_long_only(candles, [pending], quantity=Decimal("1"), profile=BacktestProfile())
    assert isinstance(result, BacktestResult)
    assert result.trades == []
    assert result.unfilled_signals == [pending.id]


def test_stop_precedes_target_when_both_are_touched() -> None:
    candles = [
        bar(0, "10", "11", "9", "10"),
        bar(1, "13", "13.5", "12.5", "13"),
        bar(2, "13", "15", "8", "12"),
    ]
    pending = signal(0)
    pending = pending.model_copy(update={"target": Decimal("14")})
    result = run_long_only(
        candles,
        [pending],
        quantity=Decimal("1"),
        profile=BacktestProfile(),
    )
    assert result.trades[0].exit_price == Decimal("9")


def test_target_exit_uses_target_price() -> None:
    candles = [
        bar(0, "10", "11", "9", "10"),
        bar(1, "13", "13.5", "12.5", "13"),
        bar(2, "13", "14.5", "12", "14"),
    ]
    pending = signal(0).model_copy(update={"target": Decimal("14")})
    result = run_long_only(
        candles,
        [pending],
        quantity=Decimal("1"),
        profile=BacktestProfile(),
    )
    assert result.trades[0].exit_price == Decimal("14")


def test_condition_exit_is_evaluated_at_close_after_protective_checks() -> None:
    candles = [
        bar(0, "10", "11", "9", "10"),
        bar(1, "13", "13.5", "12.5", "13"),
        bar(2, "13", "14", "12", "12"),
    ]
    pending = signal(0)
    result = run_long_only(
        candles,
        [pending],
        quantity=Decimal("1"),
        profile=BacktestProfile(),
        condition_exit=lambda current_signal, index, candle: index == 2,
    )
    assert result.trades[0].exit_price == Decimal("12")
