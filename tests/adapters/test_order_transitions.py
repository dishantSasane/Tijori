from decimal import Decimal

import pytest

from trading.adapters.broker import IllegalOrderTransitionError, transition
from trading.core.enums import OrderStatus
from trading.core.models import Order


def test_legal_transition_succeeds() -> None:
    order = Order(request_id="req-1", status=OrderStatus.CREATED, qty=Decimal(1))
    updated = transition(order, OrderStatus.RISK_APPROVED)
    assert updated.status == OrderStatus.RISK_APPROVED


def test_illegal_transition_raises() -> None:
    order = Order(
        request_id="req-1", status=OrderStatus.FILLED, qty=Decimal(1), qty_filled=Decimal(1)
    )
    with pytest.raises(IllegalOrderTransitionError):
        transition(order, OrderStatus.CREATED)
