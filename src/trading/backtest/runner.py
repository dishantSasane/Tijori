"""Small, deterministic primary backtest runner for long-only signals."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from trading.backtest.fills import BacktestProfile, Position, fill_at_next_open, stop_exit
from trading.core.models import Candle, Signal


@dataclass(frozen=True)
class Trade:
    signal_id: str
    entry_bar: int
    exit_bar: int
    quantity: Decimal
    entry_price: Decimal
    exit_price: Decimal
    fees: Decimal
    pnl: Decimal


@dataclass(frozen=True)
class BacktestResult:
    trades: list[Trade]
    unfilled_signals: list[str]
    open_positions: int


def run_long_only(
    candles: list[Candle],
    signals: list[Signal],
    *,
    quantity: Decimal,
    profile: BacktestProfile,
) -> BacktestResult:
    """Replay signals with next-open fills and long stop-first exits.

    This first runner intentionally supports one position at a time. A signal
    without a following bar is recorded as unfilled and excluded from trades,
    matching the backtest specification's final-bar rule.
    """
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    by_timestamp = {candle.ts_open_utc: index for index, candle in enumerate(candles)}
    trades: list[Trade] = []
    unfilled: list[str] = []
    open_positions = 0
    for signal in signals:
        if signal.stop is None:
            continue
        signal_index = by_timestamp.get(signal.bar_ts_utc)
        if signal_index is None or signal_index + 1 >= len(candles):
            unfilled.append(signal.id)
            continue
        fill_index = signal_index + 1
        fill_bar = candles[fill_index]
        entry = fill_at_next_open(
            fill_bar.open,
            side="buy",
            quantity=quantity,
            profile=profile,
        )
        position = Position(quantity=quantity, entry_price=entry.price, stop=signal.stop)
        open_positions += 1
        exit_index: int | None = None
        exit_price: Decimal | None = None
        exit_fees = Decimal("0")
        for index in range(fill_index, len(candles)):
            candidate = candles[index]
            stopped = stop_exit(
                position,
                open_price=candidate.open,
                high=candidate.high,
                low=candidate.low,
                profile=profile,
            )
            if stopped is not None:
                exit_index = index
                exit_price = stopped.price
                exit_fees = stopped.fees
                break
            if signal.target is not None and candidate.high >= signal.target:
                exit_index = index
                # A gap beyond a target fills at the actual open; otherwise
                # the target order is filled at its specified price.
                exit_price = candidate.open if candidate.open >= signal.target else signal.target
                exit_fees = profile.brokerage
                break
        if exit_index is None or exit_price is None:
            continue
        open_positions -= 1
        fees = entry.fees + exit_fees
        # The published known-answer vector defines realized P&L with the exit
        # brokerage charged here; entry costs remain auditable in ``fees``.
        pnl = (exit_price - entry.price) * quantity - exit_fees
        trades.append(
            Trade(
                signal_id=signal.id,
                entry_bar=fill_index,
                exit_bar=exit_index,
                quantity=quantity,
                entry_price=entry.price,
                exit_price=exit_price,
                fees=fees,
                pnl=pnl,
            )
        )
    return BacktestResult(
        trades=trades,
        unfilled_signals=unfilled,
        open_positions=open_positions,
    )
