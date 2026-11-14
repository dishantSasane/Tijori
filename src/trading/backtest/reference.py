"""Slow reference for checking the primary backtest runner.

The reference supports chronological, non-overlapping long entries for one
instrument. It rejects overlapping positions and is not a scorecard or a
complete strategy backtester.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

from trading.backtest.fills import BacktestProfile
from trading.backtest.runner import BacktestResult, OpenTrade, Trade
from trading.core.enums import OrderSide
from trading.core.models import Candle, Signal


def run_reference(
    candles: list[Candle],
    signals: list[Signal],
    *,
    quantity: Decimal,
    profile: BacktestProfile,
    condition_exit: Callable[[Signal, int, Candle], bool] | None = None,
) -> BacktestResult:
    """Replay entries with independent stop, target and next-open condition exits."""
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    trades: list[Trade] = []
    unfilled: list[str] = []
    audit_events: list[str] = []
    open_trades: list[OpenTrade] = []
    last_exit = -1
    last_signal = -1
    open_positions = 0
    for signal in signals:
        if signal.side != OrderSide.BUY or signal.stop is None:
            raise ValueError("reference requires a long entry with a stop")
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
            unfilled.append(signal.id)
            audit_events.append(f"rejected:concurrent_position_exists:signal_id={signal.id}")
            continue
        entry_bar = index + 1
        slip = profile.slippage_bps / Decimal("10000")
        entry_price = candles[entry_bar].open * (Decimal("1") + slip)
        open_positions = 1
        for exit_bar in range(entry_bar, len(candles)):
            bar = candles[exit_bar]
            if bar.low <= signal.stop:
                exit_reason = "stop"
                exit_price = signal.stop
                if bar.open < signal.stop:
                    exit_price = bar.open * (Decimal("1") - slip)
                    approved = abs(signal.entry_ref - signal.stop) * quantity
                    realized = abs(exit_price - signal.entry_ref) * quantity
                    audit_events.append(
                        f"gap_risk_realized:approved_risk={approved}:realized_risk={realized}"
                    )
            elif signal.target is not None and bar.high >= signal.target:
                exit_reason = "target"
                exit_price = max(bar.open, signal.target)
            elif condition_exit is not None and condition_exit(signal, exit_bar, bar):
                if exit_bar + 1 == len(candles):
                    continue
                condition_fill_bar = candles[exit_bar + 1]
                if condition_fill_bar.low <= signal.stop:
                    exit_bar += 1
                    exit_reason = "stop"
                    if condition_fill_bar.open < signal.stop:
                        exit_price = condition_fill_bar.open * (Decimal("1") - slip)
                        approved = abs(signal.entry_ref - signal.stop) * quantity
                        realized = abs(exit_price - signal.entry_ref) * quantity
                        audit_events.append(
                            f"gap_risk_realized:approved_risk={approved}:realized_risk={realized}"
                        )
                    else:
                        exit_price = signal.stop
                else:
                    exit_bar += 1
                    exit_reason = "condition"
                    exit_price = condition_fill_bar.open * (Decimal("1") - slip)
            else:
                continue
            fees = profile.entry_fee + profile.exit_fee
            trades.append(
                Trade(
                    signal_id=signal.id,
                    entry_bar=entry_bar,
                    exit_bar=exit_bar,
                    quantity=quantity,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    fees=fees,
                    pnl=(exit_price - entry_price) * quantity - fees,
                    exit_reason=exit_reason,
                )
            )
            last_exit = exit_bar
            open_positions = 0
            break
        if open_positions:
            open_trades = [
                OpenTrade(
                    signal_id=signal.id,
                    entry_bar=entry_bar,
                    quantity=quantity,
                    entry_price=entry_price,
                    fees=profile.entry_fee,
                    mark_price=candles[-1].close,
                    unrealized_pnl=(candles[-1].close - entry_price) * quantity - profile.entry_fee,
                )
            ]
    return BacktestResult(
        trades=trades,
        unfilled_signals=unfilled,
        open_positions=open_positions,
        audit_events=audit_events,
        open_trades=open_trades,
    )
