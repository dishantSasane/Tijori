from datetime import UTC, datetime

import pytest

from trading.core.clock import FixedClock, SystemClock


def test_system_clock_is_utc_aware() -> None:
    now = SystemClock().now()
    assert now.tzinfo is not None
    assert now.utcoffset() is not None and now.utcoffset().total_seconds() == 0


def test_fixed_clock_is_deterministic_and_advances() -> None:
    clock = FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
    assert clock.now() == datetime(2026, 1, 1, tzinfo=UTC)
    clock.advance(seconds=60)
    assert clock.now() == datetime(2026, 1, 1, 0, 1, tzinfo=UTC)


def test_fixed_clock_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        FixedClock(datetime(2026, 1, 1))
