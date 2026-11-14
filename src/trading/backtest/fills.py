"""Fill and stop simulation primitives for the backtester."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

Side = Literal["buy", "sell"]


@dataclass(frozen=True)
class BacktestProfile:
    """Market-specific costs; no venue assumptions belong in the engine."""

    brokerage: Decimal = Decimal("0")
    slippage_bps: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if self.brokerage < 0 or self.slippage_bps < 0:
            raise ValueError("brokerage and slippage_bps must be non-negative")


@dataclass(frozen=True)
class Fill:
    quantity: Decimal
    price: Decimal
    fees: Decimal


@dataclass(frozen=True)
class Position:
    quantity: Decimal
    entry_price: Decimal
    stop: Decimal

    def __post_init__(self) -> None:
        if self.quantity <= 0 or self.entry_price <= 0 or self.stop <= 0:
            raise ValueError("position values must be positive")
        if self.stop >= self.entry_price:
            raise ValueError("this long-only backtester requires stop < entry_price")


@dataclass(frozen=True)
class StopExit(Fill):
    gap_through_stop: bool = False


def fill_at_next_open(
    open_price: Decimal, *, side: Side, quantity: Decimal, profile: BacktestProfile
) -> Fill:
    """Fill at the next bar's open, applying adverse slippage and brokerage."""
    if open_price <= 0 or quantity <= 0:
        raise ValueError("open_price and quantity must be positive")
    slippage = profile.slippage_bps / Decimal("10000")
    if side == "buy":
        price = open_price * (Decimal("1") + slippage)
    elif side == "sell":
        price = open_price * (Decimal("1") - slippage)
    else:
        raise ValueError(f"unsupported side: {side}")
    return Fill(quantity=quantity, price=price, fees=profile.brokerage)


def stop_exit(
    position: Position,
    *,
    open_price: Decimal,
    high: Decimal,
    low: Decimal,
    profile: BacktestProfile,
) -> StopExit | None:
    """Apply long stop-first logic, including gap-through-stop at the open."""
    if open_price <= 0 or high < low:
        raise ValueError("invalid OHLC values")
    if low > position.stop:
        return None
    gap = open_price < position.stop
    if gap:
        execution_price = open_price * (Decimal("1") - profile.slippage_bps / Decimal("10000"))
    else:
        execution_price = position.stop
    return StopExit(
        quantity=position.quantity,
        price=execution_price,
        fees=profile.brokerage,
        gap_through_stop=gap,
    )
