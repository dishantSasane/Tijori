from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trading.adapters.broker import IllegalOrderTransitionError, transition
from trading.core.clock import FixedClock
from trading.core.enums import OrderStatus
from trading.core.models import Order

TS = datetime(2026, 1, 1, tzinfo=UTC)
CLOCK = FixedClock(TS)


def test_legal_transition_succeeds() -> None:
    order = Order(
        request_id="req-1", status=OrderStatus.CREATED, qty=Decimal(1), created_ts=TS, updated_ts=TS
    )
    updated = transition(order, OrderStatus.RISK_APPROVED, clock=CLOCK)
    assert updated.status == OrderStatus.RISK_APPROVED


def test_transition_stamps_updated_ts_from_clock() -> None:
    order = Order(
        request_id="req-1", status=OrderStatus.CREATED, qty=Decimal(1), created_ts=TS, updated_ts=TS
    )
    later_clock = FixedClock(datetime(2026, 1, 2, tzinfo=UTC))
    updated = transition(order, OrderStatus.RISK_APPROVED, clock=later_clock)
    assert updated.updated_ts == datetime(2026, 1, 2, tzinfo=UTC)


def test_illegal_transition_raises() -> None:
    order = Order(
        request_id="req-1",
        status=OrderStatus.FILLED,
        qty=Decimal(1),
        qty_filled=Decimal(1),
        created_ts=TS,
        updated_ts=TS,
    )
    with pytest.raises(IllegalOrderTransitionError):
        transition(order, OrderStatus.CREATED, clock=CLOCK)
