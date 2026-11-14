from datetime import UTC, datetime
from decimal import Decimal

import pytest

from tests.adapters.contract_broker import BrokerContractTests
from trading.adapters.broker import FakePaperBroker
from trading.core.clock import FixedClock
from trading.core.enums import ExitReason, MarketId
from trading.core.models import ExitRequest, Position


class TestFakePaperBroker(BrokerContractTests):
    @pytest.fixture
    def broker(self) -> FakePaperBroker:
        return FakePaperBroker(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)))

    def test_is_paper(self, broker: FakePaperBroker) -> None:
        assert broker.is_paper() is True

    def test_apply_exit_rejects_quantity_above_broker_position(
        self, broker: FakePaperBroker
    ) -> None:
        position = Position(
            market=MarketId.IN_EQUITY,
            symbol="TEST",
            sleeve="test",
            qty=Decimal("2"),
            avg_price=Decimal("100"),
            opened_ts=datetime(2026, 1, 1, tzinfo=UTC),
        )
        request = ExitRequest(
            position_id="position-1",
            quantity=Decimal("3"),
            reason_code=ExitReason.STOP,
            bar_ts_utc=datetime(2026, 1, 1, tzinfo=UTC),
            created_ts=datetime(2026, 1, 1, tzinfo=UTC),
        )
        with pytest.raises(ValueError, match="I14"):
            broker.apply_exit(request, position)
