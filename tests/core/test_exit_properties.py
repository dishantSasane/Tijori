"""Contract-level portions of the position-reducing exit invariant I14."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from trading.core.enums import ExitReason
from trading.core.models import ExitRequest


@given(st.decimals(min_value=Decimal("-1000000"), max_value=Decimal("0"), places=4))
def test_exit_quantity_must_be_strictly_positive(quantity: Decimal) -> None:
    with pytest.raises(ValidationError):
        ExitRequest(
            position_id="position-1",
            quantity=quantity,
            reason_code=ExitReason.STOP,
            created_ts=datetime(2026, 1, 1, tzinfo=UTC),
        )


@given(
    quantity=st.decimals(min_value=Decimal("0.0001"), max_value=Decimal("1000000"), places=4),
    reason=st.sampled_from(list(ExitReason)),
)
def test_positive_exit_quantities_and_reasons_are_preserved(
    quantity: Decimal, reason: ExitReason
) -> None:
    request = ExitRequest(
        position_id="position-1",
        quantity=quantity,
        reason_code=reason,
        created_ts=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert request.quantity == quantity
    assert request.reason_code == reason


@pytest.mark.parametrize("side", ["buy", "sell"])
def test_caller_cannot_choose_exit_order_side(side: str) -> None:
    with pytest.raises(ValidationError):
        ExitRequest.model_validate(
            {
                "position_id": "position-1",
                "quantity": Decimal("1"),
                "reason_code": ExitReason.STOP,
                "created_ts": datetime(2026, 1, 1, tzinfo=UTC),
                "side": side,
            }
        )
