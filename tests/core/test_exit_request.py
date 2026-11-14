from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from trading.core.enums import ExitReason
from trading.core.models import ExitRequest


def test_exit_request_has_idempotency_and_reason_fields() -> None:
    bar_ts = datetime(2026, 1, 1, 9, 15, tzinfo=UTC)
    request = ExitRequest(
        position_id="position-1",
        quantity=Decimal("2"),
        reason_code=ExitReason.STOP,
        reason_text="protective stop",
        bar_ts_utc=bar_ts,
        created_ts=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert request.exit_id
    assert request.position_id == "position-1"
    assert request.reason_code is ExitReason.STOP


def test_exit_id_is_deterministic_and_derived_from_event_identity() -> None:
    common = {
        "position_id": "position-1",
        "quantity": Decimal("2"),
        "reason_code": ExitReason.STOP,
        "bar_ts_utc": datetime(2026, 1, 1, 9, 15, tzinfo=UTC),
    }
    first = ExitRequest(**common, created_ts=datetime(2026, 1, 1, tzinfo=UTC))
    second = ExitRequest(**common, created_ts=datetime(2026, 1, 1, 9, 16, tzinfo=UTC))
    assert first.exit_id == second.exit_id

    changed = ExitRequest(
        **{**common, "reason_code": ExitReason.TARGET},
        created_ts=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert changed.exit_id != first.exit_id


def test_exit_id_cannot_be_caller_supplied() -> None:
    with pytest.raises(ValidationError):
        ExitRequest(
            position_id="position-1",
            quantity=Decimal("1"),
            reason_code=ExitReason.STOP,
            bar_ts_utc=datetime(2026, 1, 1, tzinfo=UTC),
            created_ts=datetime(2026, 1, 1, tzinfo=UTC),
            exit_id="caller-controlled",
        )


def test_exit_id_round_trips_through_serialization() -> None:
    request = ExitRequest(
        position_id="position-1",
        quantity=Decimal("1"),
        reason_code=ExitReason.STOP,
        bar_ts_utc=datetime(2026, 1, 1, tzinfo=UTC),
        created_ts=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert ExitRequest.model_validate(request.model_dump()) == request


@pytest.mark.parametrize("quantity", [Decimal("0"), Decimal("-1")])
def test_exit_request_rejects_non_positive_quantity(quantity: Decimal) -> None:
    with pytest.raises(ValidationError):
        ExitRequest(
            position_id="position-1",
            quantity=quantity,
            reason_code=ExitReason.CONDITION,
            bar_ts_utc=datetime(2026, 1, 1, tzinfo=UTC),
            created_ts=datetime(2026, 1, 1, tzinfo=UTC),
        )
