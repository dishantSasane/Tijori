from datetime import UTC, datetime

import pytest

from tests.adapters.contract_broker import BrokerContractTests
from trading.adapters.broker import FakePaperBroker
from trading.core.clock import FixedClock


class TestFakePaperBroker(BrokerContractTests):
    @pytest.fixture
    def broker(self) -> FakePaperBroker:
        return FakePaperBroker(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)))

    def test_is_paper(self, broker: FakePaperBroker) -> None:
        assert broker.is_paper() is True
