"""Pure position-reducing exit primitives (invariant I14)."""

from decimal import Decimal


def apply_exit_quantity(open_quantity: Decimal, requested_quantity: Decimal) -> Decimal:
    """Return remaining quantity, rejecting exits that could increase a position.

    The execution layer must call this after reconciling broker truth. A full
    close is represented by ``requested_quantity == open_quantity``.
    """
    if open_quantity <= 0:
        raise ValueError("open quantity must be positive")
    if requested_quantity <= 0:
        raise ValueError("exit quantity must be positive")
    if requested_quantity > open_quantity:
        raise ValueError("exit quantity exceeds open quantity (invariant I14)")
    return open_quantity - requested_quantity
