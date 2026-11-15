from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

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
    assert result.trades[0].pnl == Decimal("-460.66")


def test_final_bar_signal_is_logged_but_not_counted() -> None:
    candles = [bar(0, "10", "11", "9", "10")]
    pending = signal(0)
    result = run_long_only(candles, [pending], quantity=Decimal("1"), profile=BacktestProfile())
    assert isinstance(result, BacktestResult)
    assert result.trades == []
    assert result.unfilled_signals == [pending.id]


def test_long_only_runner_rejects_sell_signals() -> None:
    pending = signal(0).model_copy(update={"side": OrderSide.SELL})
    with pytest.raises(ValueError, match="SELL"):
        run_long_only(
            [bar(0, "10", "11", "9", "10"), bar(1, "10", "11", "9", "10")],
            [pending],
            quantity=Decimal("1"),
            profile=BacktestProfile(),
        )


def test_open_position_is_returned_at_end_of_data() -> None:
    candles = [bar(0, "10", "11", "9", "10"), bar(1, "13", "14", "12", "13")]
    result = run_long_only(candles, [signal(0)], quantity=Decimal("2"), profile=BacktestProfile())
    assert result.trades == []
    assert result.open_positions == 1
    assert result.open_trades[0].quantity == Decimal("2")


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
        bar(3, "11", "12", "10", "11"),
    ]
    pending = signal(0)
    result = run_long_only(
        candles,
        [pending],
        quantity=Decimal("1"),
        profile=BacktestProfile(),
        condition_exit=lambda current_signal, index, candle: index == 2,
    )
    assert result.trades[0].exit_price == Decimal("11")


def test_condition_exit_fill_bar_stop_precedes_condition() -> None:
    candles = [
        bar(0, "10", "11", "9", "10"),
        bar(1, "13", "13.5", "12.5", "13"),
        bar(2, "13", "14", "12", "12"),
        bar(3, "8", "9", "7", "8"),
    ]
    result = run_long_only(
        candles,
        [signal(0)],
        quantity=Decimal("1"),
        profile=BacktestProfile(slippage_bps=Decimal("5")),
        condition_exit=lambda current_signal, index, candle: index == 2,
    )
    assert result.trades[0].exit_reason == "stop"
    assert result.trades[0].exit_price == Decimal("7.9960")


@pytest.mark.parametrize("next_bar_low", ["104", "95"])
def test_condition_exit_uses_next_open_without_looking_at_later_bar_range(
    next_bar_low: str,
) -> None:
    candles = [
        bar(0, "100", "101", "99", "100"),
        bar(1, "99", "100", "98", "99"),
        bar(2, "100", "101", "99", "100"),
        bar(3, "105", "110", next_bar_low, "105"),
    ]
    result = run_long_only(
        candles,
        [signal(0).model_copy(update={"entry_ref": Decimal("100"), "stop": Decimal("96")})],
        quantity=Decimal("1"),
        profile=BacktestProfile(
            brokerage=Decimal("1"),
            entry_brokerage=Decimal("2"),
            exit_brokerage=Decimal("7"),
        ),
        condition_exit=lambda current_signal, index, candle: index == 2,
    )
    assert result.trades[0].exit_reason == "condition"
    assert result.trades[0].exit_price == Decimal("105")
    assert result.trades[0].fees == Decimal("9")
    assert result.trades[0].pnl == Decimal("-3")


def test_entry_gap_through_stop_is_realized_at_actual_fill() -> None:
    candles = [
        bar(0, "10", "11", "9", "10"),
        bar(1, "8.5", "9", "8", "8.5"),
    ]
    result = run_long_only(
        candles,
        [signal(0)],
        quantity=Decimal("1"),
        profile=BacktestProfile(brokerage=Decimal("20"), slippage_bps=Decimal("5")),
    )
    assert result.trades[0].entry_price == Decimal("8.50425")
    assert result.trades[0].exit_price == Decimal("8.49575")
    assert result.audit_events == ["gap_risk_realized:approved_risk=4:realized_risk=4.50425"]


def test_overnight_gap_through_stop_is_audited() -> None:
    candles = [
        bar(0, "10", "11", "9", "10"),
        bar(1, "13", "14", "12", "13"),
        bar(2, "13", "14", "12", "13"),
        bar(3, "8", "9", "7", "8"),
    ]
    result = run_long_only(
        candles,
        [signal(0).model_copy(update={"entry_ref": Decimal("13"), "stop": Decimal("9")})],
        quantity=Decimal("100"),
        profile=BacktestProfile(slippage_bps=Decimal("5")),
    )
    assert result.audit_events == ["gap_risk_realized:approved_risk=400:realized_risk=500.4000"]
