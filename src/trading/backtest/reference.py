"""Slow stop-only reference for checking the primary backtest runner.

The reference supports chronological, non-overlapping long entries for one
instrument. It intentionally rejects unsupported targets and overlapping
positions; it is not a scorecard or a complete strategy backtester.
"""

from __future__ import annotations

from decimal import Decimal

from trading.backtest.fills import BacktestProfile
from trading.backtest.runner import BacktestResult, Trade
from trading.core.enums import OrderSide
from trading.core.models import Candle, Signal


def run_reference(
    candles: list[Candle],
    signals: list[Signal],
    *,
    quantity: Decimal,
    profile: BacktestProfile,
) -> BacktestResult:
    """Replay each entry with an independent, bar-by-bar stop search."""
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    trades: list[Trade] = []
    unfilled: list[str] = []
    last_exit = -1
    last_signal = -1
    open_positions = 0
    for signal in signals:
        if signal.side != OrderSide.BUY or signal.stop is None or signal.target is not None:
            raise ValueError("reference supports long entries with a stop and no target")
        matching = [
            i for i, candle in enumerate(candles) if candle.ts_open_utc == signal.bar_ts_utc
        ]
        if len(matching) != 1:
            raise ValueError("signal must match exactly one candle")
        index = matching[0]
        if (candles[index].market, candles[index].symbol, candles[index].timeframe) != (
            signal.market,
            signal.symbol,
            signal.timeframe,
        ):
            raise ValueError("signal instrument does not match candle")
        if index <= last_signal:
            raise ValueError("signals must be strictly chronological")
        last_signal = index
        if index + 1 >= len(candles):
            unfilled.append(signal.id)
            continue
        if index + 1 <= last_exit or open_positions:
            raise ValueError("overlapping positions are outside reference scope")
        entry_bar = index + 1
        slip = profile.slippage_bps / Decimal("10000")
        entry_price = candles[entry_bar].open * (Decimal("1") + slip)
        open_positions = 1
        for exit_bar in range(entry_bar, len(candles)):
            bar = candles[exit_bar]
            if bar.low > signal.stop:
                continue
            exit_price = signal.stop
            if bar.open < signal.stop:
                exit_price = bar.open * (Decimal("1") - slip)
            # The published vector deducts exit brokerage only from P&L;
            # total fees separately include both entry and exit brokerage.
            trades.append(
                Trade(
                    signal_id=signal.id,
                    entry_bar=entry_bar,
                    exit_bar=exit_bar,
                    quantity=quantity,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    fees=profile.brokerage * 2,
                    pnl=(exit_price - entry_price) * quantity - profile.brokerage,
                )
            )
            last_exit = exit_bar
            open_positions = 0
            break
    return BacktestResult(trades=trades, unfilled_signals=unfilled, open_positions=open_positions)
