import pytest

from trading.indicators.technical import adx, atr, bollinger, donchian, rsi, vwap


def test_wilder_atr_known_answer() -> None:
    assert atr([10, 13, 12, 14], [9, 11, 10, 12], [10, 12, 11, 13], 2) == [
        None,
        None,
        pytest.approx(2.5),
        pytest.approx(2.75),
    ]


def test_wilder_rsi_known_answer() -> None:
    values = rsi([10, 11, 9, 10, 13], 2)
    assert values[:2] == [None, None]
    assert values[2] == pytest.approx(33.3333333333)
    assert values[3] == pytest.approx(60.0)
    assert values[4] == pytest.approx(88.2352941176)


def test_bollinger_uses_population_standard_deviation() -> None:
    middle, lower, upper = bollinger([1, 2, 3, 4, 5], 3, 2)
    assert middle[4] == pytest.approx(4.0)
    assert lower[4] == pytest.approx(2.3670068381)  # mean 4, stdev sqrt(2/3)
    assert upper[4] == pytest.approx(5.6329931619)


def test_donchian_excludes_current_bar() -> None:
    upper, lower = donchian([10, 12, 11, 15], [8, 9, 7, 10], 3)
    assert upper[:3] == [None, None, None]
    assert upper[3] == 12.0
    assert lower[3] == 7.0


def test_flat_adx_is_zero_after_warmup() -> None:
    values = adx([10] * 12, [10] * 12, [10] * 12, 3)
    assert values[-1] == 0.0


def test_vwap_uses_typical_price_and_volume() -> None:
    values = vwap([3, 4], [1, 2], [2, 3], [1, 3], period=2)
    assert values[0] == pytest.approx(2.0)
    assert values[1] == pytest.approx(2.75)
