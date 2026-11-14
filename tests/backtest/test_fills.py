from decimal import Decimal

import pytest

from trading.backtest.fills import (
    BacktestProfile,
    Position,
    fill_at_next_open,
    stop_exit,
)


def test_buy_fills_at_next_open_with_adverse_slippage() -> None:
    fill = fill_at_next_open(
        Decimal("13.2"),
        side="buy",
        quantity=Decimal("100"),
        profile=BacktestProfile(brokerage=Decimal("20"), slippage_bps=Decimal("5")),
    )
    assert fill.price == Decimal("13.2066")
    assert fill.fees == Decimal("20")


def test_stop_first_and_gap_through_stop() -> None:
    profile = BacktestProfile(brokerage=Decimal("20"), slippage_bps=Decimal("5"))
    position = Position(quantity=Decimal("100"), entry_price=Decimal("2500"), stop=Decimal("2450"))
    exit_fill = stop_exit(
        position,
        open_price=Decimal("2400"),
        high=Decimal("2600"),
        low=Decimal("2300"),
        profile=profile,
    )
    assert exit_fill is not None
    assert exit_fill.price == Decimal("2398.8")
    assert exit_fill.gap_through_stop is True
    assert exit_fill.fees == Decimal("20")


def test_stop_not_hit_returns_none() -> None:
    position = Position(quantity=Decimal("1"), entry_price=Decimal("100"), stop=Decimal("95"))
    assert (
        stop_exit(
            position,
            open_price=Decimal("99"),
            high=Decimal("101"),
            low=Decimal("96"),
            profile=BacktestProfile(),
        )
        is None
    )


def test_invalid_fill_inputs_fail_closed() -> None:
    with pytest.raises(ValueError):
        fill_at_next_open(
            Decimal("10"), side="buy", quantity=Decimal("0"), profile=BacktestProfile()
        )
