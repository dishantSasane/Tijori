from decimal import Decimal

import pytest

from trading.backtest.multiple_testing import P1_FAMILY_SIZE
from trading.backtest.ranking_report import build_ranking_report_row
from trading.backtest.runner import Trade


def trade(signal_id: str, pnl: str, *, quantity: str = "10", entry_price: str = "100") -> Trade:
    return Trade(
        signal_id=signal_id,
        entry_bar=0,
        exit_bar=1,
        quantity=Decimal(quantity),
        entry_price=Decimal(entry_price),
        exit_price=Decimal(entry_price) + Decimal(pnl) / Decimal(quantity),
        fees=Decimal("1"),
        pnl=Decimal(pnl),
    )


def daily_returns(n: int = 60) -> list[Decimal]:
    # deterministic, mildly positive-mean synthetic series -- not real data.
    return [Decimal(index % 5 - 1) / Decimal(1000) for index in range(n)]


def test_row_reports_raw_and_adjusted_p_value_side_by_side() -> None:
    trades = [trade("a", "100"), trade("b", "-20")]
    row = build_ranking_report_row(
        candidate_id="t1-donchian-v1",
        timeframe="daily",
        trades=trades,
        starting_equity=Decimal(100_000),
        daily_excess_returns=daily_returns(),
        periods_per_year=252,
        years=Decimal(1),
        bootstrap_seed=7,
    )
    assert row.candidate_id == "t1-donchian-v1"
    assert row.timeframe == "daily"
    assert row.family_size == P1_FAMILY_SIZE
    # the correction never produces a smaller p-value than the raw one.
    assert row.adjusted_p_value >= row.raw_p_value
    assert row.scorecard.trades == 2
    assert row.bootstrap_interval.sample_count == len(daily_returns())


def test_row_uses_the_caller_supplied_family_size_not_a_hardcoded_one() -> None:
    row = build_ranking_report_row(
        candidate_id="t5-orb-m1-v1",
        timeframe="intraday",
        trades=[trade("a", "10")],
        starting_equity=Decimal(100_000),
        daily_excess_returns=daily_returns(),
        periods_per_year=252,
        years=Decimal(1),
        bootstrap_seed=3,
        family_size=18,
    )
    assert row.family_size == 18
    expected = min(Decimal(1), Decimal(18) * row.raw_p_value)
    assert abs(row.adjusted_p_value - expected) < Decimal("1e-20")


def test_optional_fields_are_none_when_not_supplied() -> None:
    row = build_ranking_report_row(
        candidate_id="cash-v1",
        timeframe="daily",
        trades=[trade("a", "5")],
        starting_equity=Decimal(100_000),
        daily_excess_returns=daily_returns(),
        periods_per_year=252,
        years=Decimal(1),
        bootstrap_seed=1,
    )
    assert row.pct_profitable_instruments is None
    assert row.pct_profitable_time_windows is None
    assert row.vs_buy_and_hold_pct is None


def test_optional_fields_populate_when_supplied() -> None:
    trades = [trade("a1", "10"), trade("b1", "-5")]
    row = build_ranking_report_row(
        candidate_id="t1-donchian-v1",
        timeframe="daily",
        trades=trades,
        starting_equity=Decimal(100_000),
        daily_excess_returns=daily_returns(),
        periods_per_year=252,
        years=Decimal(1),
        bootstrap_seed=2,
        symbol_by_signal_id={"a1": "A", "b1": "B"},
        window_by_signal_id={"a1": "2026-01", "b1": "2026-02"},
        buy_and_hold_return_pct=Decimal(2),
    )
    assert row.pct_profitable_instruments == Decimal(50)
    assert row.pct_profitable_time_windows == Decimal(50)
    assert row.vs_buy_and_hold_pct is not None


def test_rejects_nonpositive_starting_equity() -> None:
    with pytest.raises(ValueError, match="positive"):
        build_ranking_report_row(
            candidate_id="a",
            timeframe="daily",
            trades=[trade("a", "1")],
            starting_equity=Decimal(0),
            daily_excess_returns=daily_returns(),
            periods_per_year=252,
            years=Decimal(1),
            bootstrap_seed=1,
        )


def test_max_drawdown_pct_is_expressed_against_starting_equity() -> None:
    trades = [trade("a", "100"), trade("b", "-300"), trade("c", "50")]
    row = build_ranking_report_row(
        candidate_id="a",
        timeframe="daily",
        trades=trades,
        starting_equity=Decimal(10_000),
        daily_excess_returns=daily_returns(),
        periods_per_year=252,
        years=Decimal(1),
        bootstrap_seed=1,
    )
    # peak after trade a (+100) = 100, trough after trade b (100-300=-200)
    # -> drawdown = 100 - (-200) = 300, as % of 10,000 starting equity = 3%.
    assert row.max_drawdown_pct == Decimal("3")
