"""Reusable Broker contract tests. A real adapter's test file should do:

    class TestMyBroker(BrokerContractTests):
        @pytest.fixture
        def broker(self) -> Broker: ...

so every broker implementation is checked against the same invariants
(docs/RISK_SPEC.md I1, I3, I7, I9).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trading.core.enums import MarketId, OrderSide, OrderStatus
from trading.core.models import OrderRequest

REQUEST_TS = datetime(2026, 1, 1, tzinfo=UTC)


def _request(**overrides: object) -> OrderRequest:
    base: dict[str, object] = dict(
        signal_id="sig-1",
        market=MarketId.IN_EQUITY,
        symbol="RELIANCE",
        side=OrderSide.BUY,
        qty=Decimal(10),
        idempotency_key="idem-1",
        created_ts=REQUEST_TS,
    )
    base.update(overrides)
    return OrderRequest(**base)  # type: ignore[arg-type]


class BrokerContractTests:
    @pytest.fixture
    def broker(self):  # pragma: no cover - overridden by subclasses
        raise NotImplementedError

    def test_place_order_fills_qty_not_over_requested(self, broker) -> None:
        order = broker.place_order(_request())
        assert order.qty_filled <= order.qty
        assert order.status in {
            OrderStatus.FILLED,
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.ROUTED,
        }

    def test_duplicate_request_id_is_idempotent(self, broker) -> None:
        request = _request()
        first = broker.place_order(request)
        second = broker.place_order(request)
        assert first.id == second.id

    def test_get_order_returns_placed_order(self, broker) -> None:
        order = broker.place_order(_request())
        assert broker.get_order(order.id).id == order.id
