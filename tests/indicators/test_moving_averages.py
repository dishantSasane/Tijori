from decimal import Decimal

import pytest

from trading.indicators.moving_averages import ema, sma


def test_sma_returns_none_until_window_is_full() -> None:
    assert sma([1.0, 2.0, 3.0, 4.0], 3) == [None, None, 2.0, 3.0]


def test_ema_uses_sma_seed_and_standard_alpha() -> None:
    values = [Decimal("1"), Decimal("2"), Decimal("3"), Decimal("4")]
    result = ema(values, 3)
    assert result[:2] == [None, None]
    assert result[2] == pytest.approx(2.0)
    assert result[3] == pytest.approx(3.0)


@pytest.mark.parametrize("period", [0, -1])
def test_moving_averages_reject_non_positive_period(period: int) -> None:
    with pytest.raises(ValueError, match="period"):
        sma([1.0, 2.0], period)
    with pytest.raises(ValueError, match="period"):
        ema([1.0, 2.0], period)
