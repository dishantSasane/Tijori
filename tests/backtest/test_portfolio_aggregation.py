from decimal import Decimal

import pytest

from trading.backtest.portfolio_aggregation import (
    PortfolioAggregation,
    aggregate_portfolio,
    daily_excess_returns,
    equal_weight_panel_returns,
    max_drawdown_pct_from_curve,
    portfolio_equity_curve,
    profitable_instrument_counts,
    weighted_panel_returns,
)


def test_equal_weight_panel_is_arithmetic_mean_per_day() -> None:
    # Day 1: (0.02 + 0.00) / 2 = 0.01. Day 2: (-0.01 + 0.03) / 2 = 0.01.
    returns = {
        "A": [Decimal("0.02"), Decimal("-0.01")],
        "B": [Decimal("0.00"), Decimal("0.03")],
    }
    panel = equal_weight_panel_returns(returns)
    assert panel == [Decimal("0.01"), Decimal("0.01")]


def test_weighted_panel_matches_hand_calculation() -> None:
    # Weights 3:1 -> normalized 0.75/0.25. Day: 0.75*0.04 + 0.25*0.00 = 0.03.
    returns = {"A": [Decimal("0.04")], "B": [Decimal("0.00")]}
    panel = weighted_panel_returns(returns, weights={"A": Decimal(3), "B": Decimal(1)})
    assert panel == [Decimal("0.03")]


def test_weighted_panel_weights_need_not_sum_to_one() -> None:
    # Raw weights 30/10 are the same ratio as 3/1 above -- same result.
    returns = {"A": [Decimal("0.04")], "B": [Decimal("0.00")]}
    panel = weighted_panel_returns(returns, weights={"A": Decimal(30), "B": Decimal(10)})
    assert panel == [Decimal("0.03")]


@pytest.mark.parametrize(
    "returns,weights,match",
    [
        ({}, {}, "at least one instrument"),
        ({"A": []}, {"A": Decimal(1)}, "must not be empty"),
        (
            {"A": [Decimal(1)], "B": [Decimal(1), Decimal(2)]},
            {"A": Decimal(1), "B": Decimal(1)},
            "same aligned length",
        ),
        (
            {"A": [Decimal(1)]},
            {"A": Decimal(1), "B": Decimal(1)},
            "exactly the supplied instruments",
        ),
        ({"A": [Decimal(1)]}, {"A": Decimal(0)}, "strictly positive"),
        ({"A": [Decimal(1)]}, {"A": Decimal(-1)}, "strictly positive"),
    ],
)
def test_weighted_panel_fails_closed(
    returns: dict[str, list[Decimal]], weights: dict[str, Decimal], match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        weighted_panel_returns(returns, weights=weights)


def test_daily_excess_returns_with_constant_cash() -> None:
    panel = [Decimal("0.02"), Decimal("0.01")]
    result = daily_excess_returns(panel, Decimal("0.005"))
    assert result == [Decimal("0.015"), Decimal("0.005")]


def test_daily_excess_returns_with_cash_series() -> None:
    panel = [Decimal("0.02"), Decimal("0.01")]
    cash = [Decimal("0.01"), Decimal("0.01")]
    assert daily_excess_returns(panel, cash) == [Decimal("0.01"), Decimal("0.00")]


def test_daily_excess_returns_rejects_mismatched_cash_series_length() -> None:
    with pytest.raises(ValueError, match="match panel_returns length"):
        daily_excess_returns([Decimal("0.01"), Decimal("0.02")], [Decimal("0.01")])


def test_portfolio_equity_curve_compounds() -> None:
    curve = portfolio_equity_curve(
        [Decimal("0.10"), Decimal("-0.10")], starting_equity=Decimal(100)
    )
    # 100 -> 110 -> 99.
    assert curve == [Decimal(100), Decimal("110.0"), Decimal("99.00")]


@pytest.mark.parametrize("bad_equity", [Decimal("Infinity"), Decimal("-Infinity"), Decimal("NaN")])
def test_portfolio_equity_curve_rejects_non_finite_starting_equity(bad_equity: Decimal) -> None:
    """BLOCKING re-review finding: starting_equity=Decimal('Infinity') passed
    the `<= 0` positivity check silently and crashed later in
    max_drawdown_pct_from_curve with decimal.InvalidOperation instead of
    being rejected at the boundary. Must raise ValueError here, immediately.
    """
    with pytest.raises(ValueError, match="finite"):
        portfolio_equity_curve([Decimal("0.01")], starting_equity=bad_equity)


def test_aggregate_portfolio_rejects_non_finite_starting_equity() -> None:
    """Same finding, exercised through the exact reproduction Codex posted:
    aggregate_portfolio({"A": [Decimal("0.01")]},
    cumulative_return_by_instrument={"A": Decimal("0.01")},
    cash_daily_returns=Decimal("0"), starting_equity=Decimal("Infinity")).
    """
    with pytest.raises(ValueError, match="finite"):
        aggregate_portfolio(
            {"A": [Decimal("0.01")]},
            cumulative_return_by_instrument={"A": Decimal("0.01")},
            cash_daily_returns=Decimal("0"),
            starting_equity=Decimal("Infinity"),
        )


def test_max_drawdown_pct_known_answer() -> None:
    # Peak 110, trough 99 -> (110-99)/110 * 100 = 10%.
    curve = [Decimal(100), Decimal("110.0"), Decimal("99.00")]
    assert max_drawdown_pct_from_curve(curve) == Decimal("10")


def test_max_drawdown_pct_zero_when_curve_only_rises() -> None:
    curve = [Decimal(100), Decimal(110), Decimal(120)]
    assert max_drawdown_pct_from_curve(curve) == Decimal(0)


def test_profitable_instrument_counts_zero_is_not_profitable() -> None:
    counts = profitable_instrument_counts(
        {"A": Decimal("0.01"), "B": Decimal("0"), "C": Decimal("-0.01")}
    )
    assert counts == (1, 3)


def test_profitable_instrument_counts_requires_at_least_one() -> None:
    with pytest.raises(ValueError, match="at least one instrument"):
        profitable_instrument_counts({})


def test_aggregate_portfolio_end_to_end_with_equal_weight_default() -> None:
    returns = {
        "A": [Decimal("0.02"), Decimal("0.00")],
        "B": [Decimal("0.00"), Decimal("0.02")],
    }
    result = aggregate_portfolio(
        returns,
        cumulative_return_by_instrument={"A": Decimal("0.02"), "B": Decimal("0.02")},
        cash_daily_returns=Decimal("0.00"),
        starting_equity=Decimal(1000),
    )
    assert isinstance(result, PortfolioAggregation)
    assert result.panel_returns == (Decimal("0.01"), Decimal("0.01"))
    assert result.excess_returns == (Decimal("0.01"), Decimal("0.01"))
    assert result.profitable_instruments == 2
    assert result.instrument_count == 2
    assert result.max_drawdown_pct == Decimal(0)


def test_aggregate_portfolio_accepts_explicit_weights() -> None:
    returns = {"A": [Decimal("0.04")], "B": [Decimal("0.00")]}
    result = aggregate_portfolio(
        returns,
        cumulative_return_by_instrument={"A": Decimal("0.04"), "B": Decimal("0.00")},
        cash_daily_returns=Decimal("0.00"),
        starting_equity=Decimal(100),
        weights={"A": Decimal(3), "B": Decimal(1)},
    )
    assert result.panel_returns == (Decimal("0.03"),)


def test_aggregate_portfolio_rejects_cumulative_return_missing_an_instrument() -> None:
    """CORRECTED BLOCKER REVIEW: panel returns must never be computed for
    one instrument set while the profitable-instrument count (which feeds
    the binomial promotion gate directly) silently reports on a different
    set. A missing key must error loudly, not compute on a mismatched set.
    """
    returns = {"A": [Decimal("0.02")], "B": [Decimal("0.00")]}
    with pytest.raises(ValueError, match="exact same instrument set"):
        aggregate_portfolio(
            returns,
            cumulative_return_by_instrument={"A": Decimal("0.02")},  # B missing
            cash_daily_returns=Decimal("0.00"),
            starting_equity=Decimal(1000),
        )


def test_aggregate_portfolio_rejects_cumulative_return_with_an_extra_instrument() -> None:
    returns = {"A": [Decimal("0.02")]}
    with pytest.raises(ValueError, match="exact same instrument set"):
        aggregate_portfolio(
            returns,
            # C is unrelated to the panel being computed (A only).
            cumulative_return_by_instrument={"A": Decimal("0.02"), "C": Decimal("0.05")},
            cash_daily_returns=Decimal("0.00"),
            starting_equity=Decimal(1000),
        )


def test_aggregate_portfolio_rejects_non_finite_returns() -> None:
    returns = {"A": [Decimal("NaN")], "B": [Decimal("0.00")]}
    with pytest.raises(ValueError, match="finite"):
        aggregate_portfolio(
            returns,
            cumulative_return_by_instrument={"A": Decimal("0.02"), "B": Decimal("0.00")},
            cash_daily_returns=Decimal("0.00"),
            starting_equity=Decimal(1000),
        )


def test_aggregate_portfolio_rejects_non_finite_weights() -> None:
    returns = {"A": [Decimal("0.02")], "B": [Decimal("0.00")]}
    with pytest.raises(ValueError, match="finite"):
        aggregate_portfolio(
            returns,
            cumulative_return_by_instrument={"A": Decimal("0.02"), "B": Decimal("0.00")},
            cash_daily_returns=Decimal("0.00"),
            starting_equity=Decimal(1000),
            weights={"A": Decimal("Infinity"), "B": Decimal(1)},
        )


def test_aggregate_portfolio_rejects_non_finite_cumulative_returns() -> None:
    returns = {"A": [Decimal("0.02")], "B": [Decimal("0.00")]}
    with pytest.raises(ValueError, match="finite"):
        aggregate_portfolio(
            returns,
            cumulative_return_by_instrument={"A": Decimal("Infinity"), "B": Decimal("0.00")},
            cash_daily_returns=Decimal("0.00"),
            starting_equity=Decimal(1000),
        )


def test_aggregate_portfolio_rejects_non_finite_cash_daily_returns() -> None:
    returns = {"A": [Decimal("0.02")]}
    with pytest.raises(ValueError, match="finite"):
        aggregate_portfolio(
            returns,
            cumulative_return_by_instrument={"A": Decimal("0.02")},
            cash_daily_returns=Decimal("NaN"),
            starting_equity=Decimal(1000),
        )


def test_weighted_panel_rejects_non_finite_returns() -> None:
    returns = {"A": [Decimal("Infinity")], "B": [Decimal("0.00")]}
    with pytest.raises(ValueError, match="finite"):
        weighted_panel_returns(returns, weights={"A": Decimal(1), "B": Decimal(1)})


def test_weighted_panel_rejects_non_finite_weights() -> None:
    returns = {"A": [Decimal("0.02")], "B": [Decimal("0.00")]}
    with pytest.raises(ValueError, match="finite"):
        weighted_panel_returns(returns, weights={"A": Decimal("NaN"), "B": Decimal(1)})
