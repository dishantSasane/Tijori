"""Small, deterministic primary backtest runner for long-only signals."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
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
    exit_reason: str = "stop"


@dataclass(frozen=True)
class BacktestResult:
    trades: list[Trade]
    unfilled_signals: list[str]
    open_positions: int
    audit_events: list[str] = field(default_factory=list)


def run_long_only(
    candles: list[Candle],
    signals: list[Signal],
    *,
    quantity: Decimal,
    profile: BacktestProfile,
    condition_exit: Callable[[Signal, int, Candle], bool] | None = None,
) -> BacktestResult:
    """Replay signals with next-open fills and long stop-first exits.

    This first runner intentionally supports one position at a time. A signal
    without a following bar is recorded as unfilled and excluded from trades,
    matching the backtest specification's final-bar rule.
    """
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    by_identity = {
        (candle.market, candle.symbol, candle.timeframe, candle.ts_open_utc): index
        for index, candle in enumerate(candles)
    }
    trades: list[Trade] = []
    unfilled: list[str] = []
    audit_events: list[str] = []
    open_positions = 0
    next_available_index: dict[tuple[object, str, object], int] = {}
    for signal in sorted(signals, key=lambda item: item.bar_ts_utc):
        if signal.stop is None:
            continue
        instrument = (signal.market, signal.symbol, signal.timeframe)
        signal_index = by_identity.get((*instrument, signal.bar_ts_utc))
        if signal_index is None or signal_index + 1 >= len(candles):
            unfilled.append(signal.id)
            continue
        fill_index = signal_index + 1
        if fill_index < next_available_index.get(instrument, 0):
            unfilled.append(signal.id)
            audit_events.append(f"rejected:concurrent_position_exists:signal_id={signal.id}")
            continue
        fill_bar = candles[fill_index]
        entry = fill_at_next_open(
            fill_bar.open,
            side="buy",
            quantity=quantity,
            profile=profile,
        )
        exit_index: int | None = None
        exit_price: Decimal | None = None
        exit_fees = Decimal("0")
        exit_reason = "stop"
        if fill_bar.open < signal.stop:
            exit_index = fill_index
            exit_price = fill_bar.open * (Decimal("1") - profile.slippage_bps / Decimal("10000"))
            exit_fees = profile.brokerage
            approved_risk = (signal.entry_ref - signal.stop) * quantity
            realized_risk = abs(exit_price - signal.entry_ref) * quantity
            audit_events.append(
                f"gap_risk_realized:approved_risk={approved_risk}:realized_risk={realized_risk}"
            )
        else:
            position = Position(quantity=quantity, entry_price=entry.price, stop=signal.stop)
        open_positions += 1
        for index in range(fill_index, len(candles)):
            if exit_index is not None:
                break
            candidate = candles[index]
            stopped = (
                stop_exit(
                    position,
                    open_price=candidate.open,
                    high=candidate.high,
                    low=candidate.low,
                    profile=profile,
                )
                if fill_bar.open >= signal.stop
                else None
            )
            if stopped is not None:
                if stopped.gap_through_stop:
                    approved_risk = abs(signal.entry_ref - signal.stop) * quantity
                    realized_risk = abs(stopped.price - signal.entry_ref) * quantity
                    audit_events.append(
                        f"gap_risk_realized:approved_risk={approved_risk}:realized_risk={realized_risk}"
                    )
                exit_index = index
                exit_price = stopped.price
                exit_fees = stopped.fees
                exit_reason = "stop"
                break
            if signal.target is not None and candidate.high >= signal.target:
                exit_index = index
                # A gap beyond a target fills at the actual open; otherwise
                # the target order is filled at its specified price.
                exit_price = candidate.open if candidate.open >= signal.target else signal.target
                exit_fees = profile.brokerage
                exit_reason = "target"
                break
            if condition_exit is not None and condition_exit(signal, index, candidate):
                exit_index = index
                exit_price = candidate.close
                exit_fees = profile.brokerage
                exit_reason = "condition"
                break
        if exit_index is None or exit_price is None:
            next_available_index[instrument] = len(candles)
            continue
        open_positions -= 1
        next_available_index[instrument] = exit_index + 1
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
                exit_reason=exit_reason,
            )
        )
    return BacktestResult(
        trades=trades,
        unfilled_signals=unfilled,
        open_positions=open_positions,
        audit_events=audit_events,
    )
