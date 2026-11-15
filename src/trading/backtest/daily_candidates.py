"""End-to-end replay for one frozen daily P1 candidate ID."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from trading.backtest.fills import BacktestProfile
from trading.backtest.runner import BacktestResult, run_long_only
from trading.core.models import Candle
from trading.indicators.moving_averages import ema, sma
from trading.indicators.technical import bollinger, rsi
from trading.strategies.daily_candidates import make_daily_exit_condition
from trading.strategies.p1_candidates import generate_p1_daily_signals, validate_p1_daily_candles
from trading.strategies.p1_catalog import get_p1_candidate


def run_p1_daily_candidate(
    candidate_id: str,
    candles: list[Candle],
    *,
    created_ts: datetime,
    quantity: Decimal,
    profile: BacktestProfile,
) -> BacktestResult:
    """Run entries, candidate-specific exits, fills, and stops for one candidate.

    This is a deterministic single-instrument replay. The caller must provide
    the already-frozen instrument window and valid action/calendar evidence;
    it does not authorize data selection or a pooled portfolio claim.
    """
    candidate = get_p1_candidate(candidate_id)
    if not candles:
        raise ValueError("daily candidate replay requires candles")
    validate_p1_daily_candles(candles)
    parameters = dict(candidate.parameters)
    closes = [float(candle.close) for candle in candles]
    exit_inputs: dict[str, Sequence[float | None]] = {}
    if candidate.family == "T2":
        exit_inputs["fast_ema"] = ema(closes, int(parameters["fast_ema"]))
        exit_inputs["slow_ema"] = ema(closes, int(parameters["slow_ema"]))
    elif candidate.family == "T4":
        exit_inputs["sma5"] = sma(closes, 5)
        exit_inputs["rsi_values"] = rsi(closes, 2)
    elif candidate.family == "T6":
        middle, _lower, _upper = bollinger(
            closes, int(parameters["period"]), float(parameters["band_width"])
        )
        exit_inputs["middle_band"] = middle

    signals = generate_p1_daily_signals(
        candidate_id,
        candles,
        created_ts=created_ts,
    )
    exit_condition = make_daily_exit_condition(candidate_id, candles, **exit_inputs)
    return run_long_only(
        candles,
        signals,
        quantity=quantity,
        profile=profile,
        condition_exit=exit_condition,
    )
