from trading.indicators.incremental import EMAState, SMAState
from trading.indicators.moving_averages import ema, sma


def test_incremental_sma_matches_batch() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    state = SMAState(3)
    assert [state.update(value) for value in values] == sma(values, 3)


def test_incremental_ema_matches_batch() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    state = EMAState(3)
    assert [state.update(value) for value in values] == ema(values, 3)
