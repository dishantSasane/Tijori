from trading.indicators.incremental import ATRState, EMAState, RSIState, SMAState
from trading.indicators.moving_averages import ema, sma
from trading.indicators.technical import atr, rsi


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
