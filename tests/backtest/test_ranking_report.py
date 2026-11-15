from decimal import Decimal

import pytest

from trading.backtest.metrics import sharpe_ratio, sortino_ratio
from trading.backtest.multiple_testing import P1_FAMILY_SIZE
from trading.backtest.ranking_report import build_ranking_report_row
from trading.backtest.runner import Trade

VALID_HASH = "a" * 64


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


def synthetic_series(n: int = 60) -> list[Decimal]:
    # deterministic, mildly positive-mean synthetic series -- not real data.
    return [Decimal(index % 5 - 1) / Decimal(1000) for index in range(n)]


def test_row_reports_raw_and_adjusted_p_value_side_by_side() -> None:
    trades = [trade("a", "100"), trade("b", "-20")]
    row = build_ranking_report_row(
        candidate_id="t1-donchian-v1",
        timeframe="daily",
        dataset_manifest_hash=VALID_HASH,
        trades=trades,
        starting_equity=Decimal(100_000),
        daily_excess_returns=synthetic_series(),
        daily_returns=synthetic_series(),
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
    assert row.bootstrap_interval.sample_count == len(synthetic_series())


def test_sharpe_sortino_use_the_daily_series_not_trade_count() -> None:
    """Regression for the per-trade/per-session unit mismatch Codex flagged:
    trade count and session count deliberately differ here (2 trades, 60
    sessions) -- if `sharpe`/`sortino` were ever computed from per-trade
    returns instead of the daily series, this would catch it, since the two
    series have different lengths and therefore different statistics.
    """
    trades = [trade("a", "100"), trade("b", "-20")]
    daily = synthetic_series(60)
    row = build_ranking_report_row(
        candidate_id="t1-donchian-v1",
        timeframe="daily",
        dataset_manifest_hash=VALID_HASH,
        trades=trades,
        starting_equity=Decimal(100_000),
        daily_excess_returns=synthetic_series(),
        daily_returns=daily,
        periods_per_year=252,
        years=Decimal(1),
        bootstrap_seed=7,
    )
    assert row.sharpe == sharpe_ratio(daily, periods_per_year=252)
    assert row.sortino == sortino_ratio(daily, periods_per_year=252)


def test_sharpe_sortino_are_none_when_daily_series_not_supplied() -> None:
    row = build_ranking_report_row(
        candidate_id="t1-donchian-v1",
        timeframe="daily",
        dataset_manifest_hash=VALID_HASH,
        trades=[trade("a", "100")],
        starting_equity=Decimal(100_000),
        daily_excess_returns=synthetic_series(),
        daily_returns=None,
        periods_per_year=252,
        years=Decimal(1),
        bootstrap_seed=7,
    )
    assert row.sharpe is None
    assert row.sortino is None


def test_row_uses_the_caller_supplied_family_size_not_a_hardcoded_one() -> None:
    row = build_ranking_report_row(
        candidate_id="t5-orb-m1-v1",
        timeframe="intraday",
        dataset_manifest_hash=VALID_HASH,
        trades=[trade("a", "10")],
        starting_equity=Decimal(100_000),
        daily_excess_returns=synthetic_series(),
        daily_returns=synthetic_series(),
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
        dataset_manifest_hash=VALID_HASH,
        trades=[trade("a", "5")],
        starting_equity=Decimal(100_000),
        daily_excess_returns=synthetic_series(),
        daily_returns=synthetic_series(),
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
        dataset_manifest_hash=VALID_HASH,
        trades=trades,
        starting_equity=Decimal(100_000),
        daily_excess_returns=synthetic_series(),
        daily_returns=synthetic_series(),
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
            dataset_manifest_hash=VALID_HASH,
            trades=[trade("a", "1")],
            starting_equity=Decimal(0),
            daily_excess_returns=synthetic_series(),
            daily_returns=synthetic_series(),
            periods_per_year=252,
            years=Decimal(1),
            bootstrap_seed=1,
        )


@pytest.mark.parametrize(
    "bad_hash",
    [
        "",
        "synthetic-manifest-sha256",  # not hex at all
        "A" * 64,  # uppercase hex rejected -- must be lowercase
        "a" * 63,  # too short
        "a" * 65,  # too long
    ],
)
def test_rejects_non_sha256_dataset_manifest_hash(bad_hash: str) -> None:
    with pytest.raises(ValueError, match="dataset_manifest_hash"):
        build_ranking_report_row(
            candidate_id="a",
            timeframe="daily",
            dataset_manifest_hash=bad_hash,
            trades=[trade("a", "1")],
            starting_equity=Decimal(1_000),
            daily_excess_returns=synthetic_series(),
            daily_returns=synthetic_series(),
            periods_per_year=252,
            years=Decimal(1),
            bootstrap_seed=1,
        )


def test_max_drawdown_pct_is_expressed_against_starting_equity() -> None:
    trades = [trade("a", "100"), trade("b", "-300"), trade("c", "50")]
    row = build_ranking_report_row(
        candidate_id="a",
        timeframe="daily",
        dataset_manifest_hash=VALID_HASH,
        trades=trades,
        starting_equity=Decimal(10_000),
        daily_excess_returns=synthetic_series(),
        daily_returns=synthetic_series(),
        periods_per_year=252,
        years=Decimal(1),
        bootstrap_seed=1,
    )
    # peak after trade a (+100) = 100, trough after trade b (100-300=-200)
    # -> drawdown = 100 - (-200) = 300, as % of 10,000 starting equity = 3%.
    assert row.max_drawdown_pct == Decimal("3")
