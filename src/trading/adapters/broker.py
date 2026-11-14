"""Broker Protocol + a paper fake. Real adapters (Kite Connect, Alpaca, CCXT)
are built in P1+. `is_paper()` backs invariant I1 (docs/RISK_SPEC.md):
in paper mode, a real-broker adapter must never be constructed/called.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from trading.core.enums import ORDER_STATUS_TRANSITIONS, OrderStatus
from trading.core.models import Fill, Order, OrderRequest, Position


class IllegalOrderTransitionError(RuntimeError):
    """Raised on any transition not in ORDER_STATUS_TRANSITIONS (fail closed)."""


class Broker(Protocol):
    def is_paper(self) -> bool: ...

    def place_order(self, request: OrderRequest) -> Order: ...

    def cancel_order(self, order_id: str) -> Order: ...

    def get_order(self, order_id: str) -> Order: ...

    def positions(self) -> list[Position]: ...


def transition(order: Order, new_status: OrderStatus) -> Order:
    """Apply a status transition, raising if it is illegal (docs/RISK_SPEC.md §6)."""
    if new_status not in ORDER_STATUS_TRANSITIONS[order.status]:
        raise IllegalOrderTransitionError(f"{order.status} -> {new_status} is not allowed")
    return order.model_copy(update={"status": new_status})


class FakePaperBroker:
    """Fills every order immediately at the order's limit price (or signal
    entry_ref if market) with zero slippage. Good enough for adapter contract
    tests; the real paper broker (with costs/slippage) is a P2 deliverable.
    """

    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}
        self._fills: list[Fill] = []
        self._positions: dict[tuple[str, str], Position] = {}

    def is_paper(self) -> bool:
        return True

    def place_order(self, request: OrderRequest) -> Order:
        if request.id in self._orders:
            # Idempotency (invariant I7): same request id never places twice.
            return self._orders[request.id]
        order = Order(
            id=request.id, request_id=request.id, status=OrderStatus.CREATED, qty=request.qty
        )
        order = transition(order, OrderStatus.RISK_APPROVED)
        order = transition(order, OrderStatus.ROUTED)
        order = transition(order, OrderStatus.FILLED)
        order = order.model_copy(
            update={
                "qty_filled": order.qty,
                "avg_fill_price": request.limit_price or Decimal(1),
            }
        )
        self._orders[order.id] = order
        return order

    def cancel_order(self, order_id: str) -> Order:
        order = self._orders[order_id]
        order = transition(order, OrderStatus.CANCELLED)
        self._orders[order_id] = order
        return order

    def get_order(self, order_id: str) -> Order:
        return self._orders[order_id]

    def positions(self) -> list[Position]:
        return list(self._positions.values())
