from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from trading.core.enums import ExitReason
from trading.core.models import ExitRequest


def test_exit_request_has_idempotency_and_reason_fields() -> None:
    request = ExitRequest(
        position_id="position-1",
        quantity=Decimal("2"),
        reason_code=ExitReason.STOP,
        reason_text="protective stop",
        created_ts=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert request.exit_id
    assert request.position_id == "position-1"
    assert request.reason_code is ExitReason.STOP


@pytest.mark.parametrize("quantity", [Decimal("0"), Decimal("-1")])
def test_exit_request_rejects_non_positive_quantity(quantity: Decimal) -> None:
    with pytest.raises(ValidationError):
        ExitRequest(
            position_id="position-1",
            quantity=quantity,
            reason_code=ExitReason.CONDITION,
            created_ts=datetime(2026, 1, 1, tzinfo=UTC),
        )
