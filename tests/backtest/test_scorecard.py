from decimal import Decimal

from trading.backtest.runner import Trade
from trading.backtest.scorecard import scorecard


def trade(pnl: str, index: int) -> Trade:
    return Trade(
        signal_id=str(index),
        entry_bar=index,
        exit_bar=index + 1,
        quantity=Decimal("1"),
        entry_price=Decimal("100"),
        exit_price=Decimal("100"),
        fees=Decimal("0"),
        pnl=Decimal(pnl),
    )


def test_scorecard_reports_trade_metrics_and_drawdown() -> None:
    result = scorecard([trade("10", 0), trade("-4", 2), trade("-6", 4)])
    assert result.trades == 3
    assert result.wins == 1
    assert result.losses == 2
    assert result.total_pnl == Decimal("0")
    assert result.win_rate == Decimal("0.3333333333333333333333333333")
    assert result.max_drawdown == Decimal("10")
    assert result.avg_win == Decimal("10")
    assert result.avg_loss == Decimal("-5")
    assert result.expectancy == Decimal("0")


def test_empty_scorecard_is_zeroed() -> None:
    result = scorecard([])
    assert result.trades == 0
    assert result.total_pnl == Decimal("0")
    assert result.win_rate == Decimal("0")
    assert result.avg_win == Decimal("0")
    assert result.avg_loss == Decimal("0")
    assert result.expectancy == Decimal("0")
