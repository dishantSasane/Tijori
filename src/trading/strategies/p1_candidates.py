"""Execute a frozen daily P1 candidate ID without caller-chosen parameters."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from trading.core.enums import Timeframe
from trading.core.models import Candle, Signal
from trading.indicators.moving_averages import ema, sma
from trading.indicators.technical import adx, atr, bollinger, rsi
from trading.strategies.daily_candidates import t2_ema_adx, t6_bollinger_reversion
from trading.strategies.p1_catalog import get_p1_candidate
from trading.strategies.phase1 import t1_donchian, t4_rsi_pullback


def generate_p1_daily_signals(
    candidate_id: str,
    candles: Sequence[Candle],
    *,
    created_ts: datetime,
) -> list[Signal]:
    """Compute causal indicators and emit entries for a frozen daily candidate.

    All indicators at position ``i`` use candles through ``i`` only. Signal
    timestamps refer to the triggering closed bar; the shared runner handles
    the next-open fill and stop-first protective exit.
    """
    candidate = get_p1_candidate(candidate_id)
    if candidate.timeframe != Timeframe.D1.value:
        raise ValueError("daily signal generation requires a daily P1 candidate")
    if not candles:
        return []
    first = candles[0]
    if any(
        candle.market != first.market
        or candle.symbol != first.symbol
        or candle.timeframe is not Timeframe.D1
        for candle in candles
    ):
        raise ValueError("daily candidate input must be one symbol's daily candles")

    closes = [float(candle.close) for candle in candles]
    highs = [float(candle.high) for candle in candles]
    lows = [float(candle.low) for candle in candles]
    atr_values = atr(highs, lows, closes, 14)
    parameters = dict(candidate.parameters)

    if candidate.family == "T1":
        return t1_donchian(
            candles,
            atr_values,
            lookback=int(parameters["entry_n"]),
            exit_lookback=int(parameters["exit_m"]),
            atr_multiple=float(parameters["atr_k"]),
            strategy_version=candidate_id,
            created_ts=created_ts,
        )
    if candidate.family == "T2":
        fast_period = int(parameters["fast_ema"])
        slow_period = int(parameters["slow_ema"])
        return t2_ema_adx(
            candles,
            ema(closes, fast_period),
            ema(closes, slow_period),
            adx(highs, lows, closes, 14),
            atr_values,
            adx_threshold=float(parameters["adx_threshold"]),
            atr_multiple=float(parameters["atr_k"]),
            strategy_version=candidate_id,
            created_ts=created_ts,
        )
    if candidate.family == "T4":
        return t4_rsi_pullback(
            candles,
            sma(closes, 200),
            rsi(closes, 2),
            atr_values,
            rsi_threshold=float(parameters["rsi_threshold"]),
            atr_multiple=float(parameters["atr_k"]),
            strategy_version=candidate_id,
            created_ts=created_ts,
        )
    if candidate.family == "T6":
        middle, lower, _upper = bollinger(
            closes, int(parameters["period"]), float(parameters["band_width"])
        )
        return t6_bollinger_reversion(
            candles,
            lower,
            middle,
            adx(highs, lows, closes, 14),
            atr_values,
            adx_maximum=float(parameters["adx_max"]),
            atr_multiple=float(parameters["atr_k"]),
            strategy_version=candidate_id,
            created_ts=created_ts,
        )
    raise ValueError(f"candidate {candidate_id} is not a daily entry strategy")
