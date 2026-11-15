from decimal import Decimal, localcontext

import pytest

from trading.backtest.metrics import (
    TurnoverAndCosts,
    annualized_return_pct,
    bootstrap_mean_return_interval,
    calmar_ratio,
    pct_profitable_instruments,
    pct_profitable_time_windows,
    sharpe_ratio,
    sortino_ratio,
    trade_returns,
    turnover_and_cost_sensitivity,
    vs_buy_and_hold_pct,
)
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


def _close(actual: Decimal, expected: Decimal, *, places: int = 10) -> bool:
    with localcontext() as context:
        context.prec = 40
        return abs(actual - expected) < Decimal(10) ** -places


def test_trade_returns_is_pnl_over_starting_equity() -> None:
    trades = [trade("a", "100"), trade("b", "-50")]
    returns = trade_returns(trades, starting_equity=Decimal(1000))
    assert returns == [Decimal("0.1"), Decimal("-0.05")]


def test_trade_returns_rejects_nonpositive_equity() -> None:
    with pytest.raises(ValueError, match="positive"):
        trade_returns([trade("a", "1")], starting_equity=Decimal(0))


def test_sharpe_ratio_known_answer() -> None:
    # mean=0.02, sample stdev=sqrt(0.0002) -> ratio is exactly sqrt(2) at ppy=1.
    returns = [Decimal("0.01"), Decimal("0.03")]
    result = sharpe_ratio(returns, periods_per_year=1)
    with localcontext() as context:
        context.prec = 40
        expected = Decimal(2).sqrt()
    assert _close(result, expected)


def test_sharpe_ratio_zero_variance_is_zero_not_a_crash() -> None:
    assert sharpe_ratio([Decimal("0.01"), Decimal("0.01")], periods_per_year=12) == Decimal(0)


def test_sharpe_ratio_too_few_periods_is_zero() -> None:
    assert sharpe_ratio([Decimal("0.01")], periods_per_year=12) == Decimal(0)


def test_sharpe_ratio_rejects_nonpositive_periods_per_year() -> None:
    with pytest.raises(ValueError, match="periods_per_year"):
        sharpe_ratio([Decimal("0.01"), Decimal("0.02")], periods_per_year=0)


def test_sortino_ratio_known_answer() -> None:
    # downside_sq = ((0)^2 + (-0.04)^2) / 2 = 0.0008 -> downside = sqrt(0.0008)
    # mean = -0.01 -> sortino = -0.01 / sqrt(0.0008) at ppy=1.
    returns = [Decimal("0.02"), Decimal("-0.04")]
    result = sortino_ratio(returns, periods_per_year=1)
    with localcontext() as context:
        context.prec = 40
        expected = Decimal("-0.01") / Decimal("0.0008").sqrt()
    assert _close(result, expected)


def test_sortino_ratio_no_downside_is_zero() -> None:
    assert sortino_ratio([Decimal("0.01"), Decimal("0.02")], periods_per_year=12) == Decimal(0)


def test_sortino_ratio_empty_is_zero() -> None:
    assert sortino_ratio([], periods_per_year=12) == Decimal(0)


def test_annualized_return_pct_one_year_is_identity() -> None:
    assert annualized_return_pct(total_return_pct=Decimal(25), years=Decimal(1)) == Decimal(25)


def test_annualized_return_pct_compounds_over_multiple_years() -> None:
    # 100% total return over 2 years -> sqrt(2) - 1 annualized, as a percentage.
    result = annualized_return_pct(total_return_pct=Decimal(100), years=Decimal(2))
    with localcontext() as context:
        context.prec = 40
        expected = (Decimal(2).sqrt() - Decimal(1)) * Decimal(100)
    assert _close(result, expected)


def test_annualized_return_pct_floors_total_wipeout_at_minus_100() -> None:
    assert annualized_return_pct(total_return_pct=Decimal(-150), years=Decimal(3)) == Decimal(-100)


def test_annualized_return_pct_rejects_nonpositive_years() -> None:
    with pytest.raises(ValueError, match="years"):
        annualized_return_pct(total_return_pct=Decimal(10), years=Decimal(0))


def test_calmar_ratio_known_answer() -> None:
    result = calmar_ratio(annualized_return_pct=Decimal(20), max_drawdown_pct=Decimal(10))
    assert result == Decimal(2)


def test_calmar_ratio_zero_drawdown_is_zero() -> None:
    assert calmar_ratio(annualized_return_pct=Decimal(20), max_drawdown_pct=Decimal(0)) == Decimal(
        0
    )


def test_turnover_and_cost_sensitivity_known_answer() -> None:
    trades = [
        trade("a", "50", quantity="10", entry_price="100"),  # notional 1000
        trade("b", "-20", quantity="5", entry_price="200"),  # notional 1000
    ]
    result = turnover_and_cost_sensitivity(trades, starting_equity=Decimal(1000))
    assert result == TurnoverAndCosts(
        turnover_ratio=Decimal(2),  # 2000 notional / 1000 equity
        cost_pct_of_notional=Decimal("0.001"),  # 2 total fees / 2000 notional
    )


def test_turnover_and_cost_sensitivity_no_trades() -> None:
    result = turnover_and_cost_sensitivity([], starting_equity=Decimal(1000))
    assert result == TurnoverAndCosts(Decimal(0), Decimal(0))


def test_pct_profitable_instruments_known_answer() -> None:
    trades = [
        trade("a1", "10"),
        trade("a2", "-5"),  # net for A: +5 -> profitable
        trade("b1", "-20"),  # net for B: -20 -> not profitable
    ]
    symbols = {"a1": "A", "a2": "A", "b1": "B"}
    assert pct_profitable_instruments(trades, symbol_by_signal_id=symbols) == Decimal(50)


def test_pct_profitable_instruments_requires_a_label_for_every_trade() -> None:
    with pytest.raises(KeyError):
        pct_profitable_instruments([trade("a", "1")], symbol_by_signal_id={})


def test_pct_profitable_time_windows_known_answer() -> None:
    trades = [trade("a", "10"), trade("b", "-3")]
    windows = {"a": "2026-01", "b": "2026-02"}
    assert pct_profitable_time_windows(trades, window_by_signal_id=windows) == Decimal(50)


def test_vs_buy_and_hold_pct_is_excess_return() -> None:
    result = vs_buy_and_hold_pct(
        strategy_total_return_pct=Decimal(15), buy_and_hold_return_pct=Decimal(8)
    )
    assert result == Decimal(7)


def test_bootstrap_mean_return_interval_delegates_to_existing_bootstrap() -> None:
    returns = [Decimal(index % 5 - 2) / Decimal(100) for index in range(50)]
    result = bootstrap_mean_return_interval(returns, block_size=5, replicates=200, seed=7)
    assert result.sample_count == 50
    assert result.seed == 7
    assert result.lower <= result.upper
