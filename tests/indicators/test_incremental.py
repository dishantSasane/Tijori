from trading.indicators.incremental import (
    ADXState,
    ATRState,
    BollingerState,
    DonchianState,
    EMAState,
    RSIState,
    SMAState,
    VWAPState,
)
from trading.indicators.moving_averages import ema, sma
from trading.indicators.technical import adx, atr, bollinger, donchian, rsi, vwap


def test_incremental_sma_matches_batch() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    state = SMAState(3)
    assert [state.update(value) for value in values] == sma(values, 3)


def test_incremental_ema_matches_batch() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    state = EMAState(3)
    assert [state.update(value) for value in values] == ema(values, 3)


def test_incremental_rsi_matches_batch() -> None:
    values = [10, 11, 9, 10, 13]
    state = RSIState(2)
    assert [state.update(value) for value in values] == rsi(values, 2)


def test_incremental_atr_matches_batch() -> None:
    highs, lows, closes = [10, 13, 12, 14], [9, 11, 10, 12], [10, 12, 11, 13]
    state = ATRState(2)
    actual = [
        state.update(high, low, close)
        for high, low, close in zip(highs, lows, closes, strict=False)
    ]
    assert actual == atr(highs, lows, closes, 2)


def test_incremental_bollinger_matches_batch() -> None:
    values = [1, 2, 3, 4, 5]
    state = BollingerState(3, 2)
    actual = [state.update(value) for value in values]
    middle, lower, upper = bollinger(values, 3, 2)
    expected = [
        None if item[0] is None else (item[0], item[1], item[2])
        for item in zip(middle, lower, upper, strict=True)
    ]
    assert actual == expected


def test_incremental_donchian_matches_batch() -> None:
    highs, lows = [10, 12, 11, 15], [8, 9, 7, 10]
    state = DonchianState(3)
    actual = [state.update(high, low) for high, low in zip(highs, lows, strict=True)]
    upper, lower = donchian(highs, lows, 3)
    assert actual == [
        None if top is None else (top, bottom) for top, bottom in zip(upper, lower, strict=True)
    ]


def test_incremental_vwap_matches_batch() -> None:
    highs, lows, closes, volumes = [3, 4], [1, 2], [2, 3], [1, 3]
    state = VWAPState(2)
    actual = [
        state.update(high, low, close, volume)
        for high, low, close, volume in zip(highs, lows, closes, volumes, strict=True)
    ]
    assert actual == vwap(highs, lows, closes, volumes, 2)


def test_incremental_adx_matches_batch() -> None:
    highs = [10.0, 11.0, 12.5, 11.8, 13.2, 14.0, 13.6, 15.1, 14.8, 16.0, 17.2, 16.4]
    lows = [8.0, 9.0, 10.5, 10.0, 11.4, 12.2, 11.8, 13.0, 12.5, 14.0, 15.0, 14.2]
    closes = [9.0, 10.5, 11.2, 10.8, 12.7, 13.5, 12.4, 14.6, 13.2, 15.5, 16.8, 15.0]
    state = ADXState(3)
    actual = [
        state.update(high, low, close) for high, low, close in zip(highs, lows, closes, strict=True)
    ]
    assert actual == adx(highs, lows, closes, 3)
