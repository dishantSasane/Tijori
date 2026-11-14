"""Known-answer and cross-runner tests for the stop-and-target reference."""

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st
from test_runner import bar, signal

from trading.backtest.fills import BacktestProfile
from trading.backtest.reference import run_reference
from trading.backtest.runner import Trade, run_long_only
from trading.core.models import Candle, Signal
from trading.strategies.phase1 import t1_donchian, t4_rsi_pullback


@pytest.mark.parametrize("same_bar", [True, False])
def test_known_stop_vector_matches_both_runners(same_bar: bool) -> None:
    bars = [
        bar(0, "10", "11", "9", "10"),
        bar(1, "13.2", "13.5", "8.5" if same_bar else "13", "13.3"),
        bar(2, "9.5", "14", "8", "13"),
    ]
    entry = signal(0)
    profile = BacktestProfile(brokerage=Decimal("20"), slippage_bps=Decimal("5"))
    expected = Trade(
        entry.id,
        1,
        1 if same_bar else 2,
        Decimal("100"),
        Decimal("13.2066"),
        Decimal("9"),
        Decimal("40"),
        Decimal("-460.66"),
    )
    for runner in (run_reference, run_long_only):
        result = runner(bars, [entry], quantity=Decimal("100"), profile=profile)
        assert result.trades == [expected]
        assert result.open_positions == 0
        assert result.unfilled_signals == []


def test_final_signal_and_open_position_match() -> None:
    bars = [bar(0, "10", "11", "9", "10"), bar(1, "13", "14", "12", "13")]
    pending = signal(1)
    filled = signal(0)
    for entry in (pending, filled):
        reference = run_reference(bars, [entry], quantity=Decimal("1"), profile=BacktestProfile())
        primary = run_long_only(bars, [entry], quantity=Decimal("1"), profile=BacktestProfile())
        assert reference == primary
    assert run_reference(
        bars, [pending], quantity=Decimal("1"), profile=BacktestProfile()
    ).unfilled_signals == [pending.id]
    assert (
        run_reference(
            bars, [filled], quantity=Decimal("1"), profile=BacktestProfile()
        ).open_positions
        == 1
    )


def test_reference_handles_gap_below_stop_on_fill_bar() -> None:
    bars = [bar(0, "2500", "2510", "2490", "2500"), bar(1, "2400", "2420", "2390", "2410")]
    entry = signal(0).model_copy(update={"entry_ref": Decimal("2500"), "stop": Decimal("2450")})
    profile = BacktestProfile(brokerage=Decimal("20"), slippage_bps=Decimal("5"))
    result = run_reference(bars, [entry], quantity=Decimal("100"), profile=profile)
    assert result == run_long_only(bars, [entry], quantity=Decimal("100"), profile=profile)
    assert result.trades == [
        Trade(
            entry.id,
            1,
            1,
            Decimal("100"),
            Decimal("2401.2"),
            Decimal("2398.8"),
            Decimal("40"),
            Decimal("-280.0"),
        )
    ]


def test_asymmetric_entry_and_exit_fees_are_both_charged() -> None:
    bars = [bar(0, "10", "11", "9", "10"), bar(1, "13", "14", "8", "13")]
    profile = BacktestProfile(
        brokerage=Decimal("0"),
        entry_brokerage=Decimal("15"),
        exit_brokerage=Decimal("25"),
    )
    result = run_reference(bars, [signal(0)], quantity=Decimal("1"), profile=profile)
    assert result.trades[0].fees == Decimal("40")
    assert result.trades[0].pnl == Decimal("-44")


def test_t1_and_t4_signals_produce_identical_trade_lists() -> None:
    t1_bars = [
        bar(0, "10", "10", "9", "10"),
        bar(1, "11", "11", "10", "11"),
        bar(2, "9", "9", "8", "9"),
        bar(3, "10", "10", "9", "10"),
        bar(4, "13", "13", "12", "13"),
        bar(5, "13.2", "13.5", "8.5", "13.3"),
    ]
    t1_signals = t1_donchian(
        t1_bars, [None, None, None, None, 2, None], lookback=3, created_ts=t1_bars[0].ingest_ts
    )
    t4_bars = [bar(0, "105", "106", "104", "105"), bar(1, "105", "106", "99", "105")]
    t4_signals = t4_rsi_pullback(
        t4_bars, [100, None], [8, None], [2, None], created_ts=t4_bars[0].ingest_ts
    )
    for bars, signals in ((t1_bars, t1_signals), (t4_bars, t4_signals)):
        assert len(signals) == 1
        for profile in (BacktestProfile(), BacktestProfile(Decimal("20"), Decimal("5"))):
            actual = run_long_only(bars, signals, quantity=Decimal("100"), profile=profile)
            expected = run_reference(bars, signals, quantity=Decimal("100"), profile=profile)
            assert len(expected.trades) == 1
            assert actual == expected


def test_gap_after_entry_matches_and_uses_adverse_slippage() -> None:
    bars = [
        bar(0, "10", "11", "9", "10"),
        bar(1, "13", "14", "12", "13"),
        bar(2, "8", "10", "7", "9"),
    ]
    entry = signal(0)
    profile = BacktestProfile(Decimal("20"), Decimal("5"))
    reference = run_reference(bars, [entry], quantity=Decimal("100"), profile=profile)
    assert reference.trades[0].exit_price == Decimal("7.9960")
    assert reference == run_long_only(bars, [entry], quantity=Decimal("100"), profile=profile)


@given(
    open_price=st.integers(min_value=10, max_value=10000),
    stop_distance=st.integers(min_value=1, max_value=9),
    slip=st.integers(min_value=0, max_value=100),
    fees=st.integers(min_value=0, max_value=100),
)
def test_equivalence_for_varied_stops_and_costs(
    open_price: int, stop_distance: int, slip: int, fees: int
) -> None:
    stop = open_price - stop_distance
    bars = [
        bar(0, str(open_price), str(open_price + 1), str(open_price - 1), str(open_price)),
        bar(1, str(open_price), str(open_price + 1), str(stop), str(open_price)),
    ]
    entry = signal(0).model_copy(update={"entry_ref": Decimal(open_price), "stop": Decimal(stop)})
    profile = BacktestProfile(Decimal(fees), Decimal(slip))
    reference = run_reference(bars, [entry], quantity=Decimal("3"), profile=profile)
    assert len(reference.trades) == 1
    assert reference == run_long_only(bars, [entry], quantity=Decimal("3"), profile=profile)


def test_reference_rejects_overlapping_positions() -> None:
    bars = [
        bar(0, "10", "11", "9", "10"),
        bar(1, "13", "14", "12", "13"),
        bar(2, "13", "14", "12", "13"),
    ]
    with pytest.raises(ValueError, match="overlapping"):
        run_reference(
            bars, [signal(0), signal(1)], quantity=Decimal("1"), profile=BacktestProfile()
        )


@pytest.mark.parametrize(
    ("opening", "high", "low", "expected_price", "expected_reason"),
    [
        ("13", "15", "12", "14", "target"),
        ("15", "16", "12", "15", "target"),
        ("13", "15", "8", "9", "stop"),
    ],
)
def test_target_and_stop_precedence_matches(
    opening: str, high: str, low: str, expected_price: str, expected_reason: str
) -> None:
    bars = [bar(0, "10", "11", "9", "10"), bar(1, opening, high, low, opening)]
    entry = signal(0).model_copy(update={"target": Decimal("14")})
    profile = BacktestProfile(Decimal("20"), Decimal("5"))
    reference = run_reference(bars, [entry], quantity=Decimal("100"), profile=profile)
    assert reference.trades[0].exit_price == Decimal(expected_price)
    assert reference.trades[0].exit_reason == expected_reason
    assert reference == run_long_only(bars, [entry], quantity=Decimal("100"), profile=profile)


def test_zero_slippage_entry_gap_matches_both_runners() -> None:
    bars = [bar(0, "2500", "2510", "2490", "2500"), bar(1, "2400", "2420", "2390", "2410")]
    entry = signal(0).model_copy(update={"entry_ref": Decimal("2500"), "stop": Decimal("2450")})
    profile = BacktestProfile(brokerage=Decimal("20"))
    reference = run_reference(bars, [entry], quantity=Decimal("100"), profile=profile)
    assert reference.trades[0].entry_price == Decimal("2400")
    assert reference.trades[0].exit_price == Decimal("2400")
    assert reference.audit_events == ["gap_risk_realized:approved_risk=5000:realized_risk=10000"]
    assert reference == run_long_only(bars, [entry], quantity=Decimal("100"), profile=profile)


@pytest.mark.parametrize("strategy", ["t1", "t4_sma", "t4_rsi", "t4_time", "t6_band", "t6_time"])
def test_condition_exit_on_closed_bar_fills_next_open(strategy: str) -> None:
    bars = [
        bar(0, "13", "14", "12", "13"),
        bar(1, "13", "14", "10", "11"),
        bar(2, "12", "13", "10", "12"),
    ]
    entry = signal(0)

    def exit_rule(current_signal: Signal, index: int, candle: Candle) -> bool:
        if strategy == "t1":
            return candle.close < bars[index - 1].low
        if strategy.startswith("t4"):
            sma5 = Decimal("10") if strategy == "t4_sma" else Decimal("20")
            rsi2 = Decimal("71") if strategy == "t4_rsi" else Decimal("50")
            bars_held = 5 if strategy == "t4_time" else 1
            return candle.close > sma5 or rsi2 > 70 or bars_held >= 5
        middle = Decimal("11") if strategy == "t6_band" else Decimal("20")
        bars_held = 10 if strategy == "t6_time" else 1
        return candle.close >= middle or bars_held >= 10

    profile = BacktestProfile(Decimal("20"), Decimal("5"))
    reference = run_reference(
        bars, [entry], quantity=Decimal("100"), profile=profile, condition_exit=exit_rule
    )
    assert reference == run_long_only(
        bars, [entry], quantity=Decimal("100"), profile=profile, condition_exit=exit_rule
    )
    assert reference.trades == [
        Trade(
            entry.id,
            1,
            2,
            Decimal("100"),
            Decimal("13.0065"),
            Decimal("11.9940"),
            Decimal("40"),
            Decimal("-121.2500"),
            "condition",
        )
    ]
    assert reference.open_positions == 0


def test_final_bar_condition_exit_remains_unfilled() -> None:
    bars = [bar(0, "13", "14", "12", "13"), bar(1, "13", "14", "10", "11")]
    entry = signal(0)

    def callback(current_signal: Signal, index: int, candle: Candle) -> bool:
        return True

    reference = run_reference(
        bars, [entry], quantity=Decimal("1"), profile=BacktestProfile(), condition_exit=callback
    )
    assert reference == run_long_only(
        bars, [entry], quantity=Decimal("1"), profile=BacktestProfile(), condition_exit=callback
    )
    assert reference.trades == []
    assert reference.open_positions == 1


def test_stop_takes_precedence_over_condition_exit() -> None:
    bars = [
        bar(0, "13", "14", "12", "13"),
        bar(1, "13", "14", "8", "11"),
        bar(2, "12", "13", "10", "12"),
    ]
    entry = signal(0)

    def callback(current_signal: Signal, index: int, candle: Candle) -> bool:
        return True

    reference = run_reference(
        bars, [entry], quantity=Decimal("1"), profile=BacktestProfile(), condition_exit=callback
    )
    assert reference == run_long_only(
        bars, [entry], quantity=Decimal("1"), profile=BacktestProfile(), condition_exit=callback
    )
    assert reference.trades[0].exit_reason == "stop"
    assert reference.trades[0].exit_price == Decimal("9")
