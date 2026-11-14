import pytest

from tests.adapters.contract_broker import BrokerContractTests
from trading.adapters.broker import FakePaperBroker


class TestFakePaperBroker(BrokerContractTests):
    @pytest.fixture
    def broker(self) -> FakePaperBroker:
        return FakePaperBroker()

    def test_is_paper(self, broker: FakePaperBroker) -> None:
        assert broker.is_paper() is True
