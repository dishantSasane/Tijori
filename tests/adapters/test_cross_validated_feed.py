from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trading.adapters.cross_validated_feed import detect_discrepancies
from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle

TS = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
INGEST = datetime(2026, 1, 1, 10, 1, tzinfo=UTC)


def _candle(close: str, *, source: str, ts: datetime = TS) -> Candle:
    return Candle(
        market=MarketId.IN_EQUITY,
        symbol="RELIANCE",
        timeframe=Timeframe.D1,
        ts_open_utc=ts,
        open=Decimal(close),
        high=Decimal(close),
        low=Decimal(close),
        close=Decimal(close),
        volume=Decimal(1000),
        source=source,
        ingest_ts=INGEST,
    )


def test_agreeing_feeds_produce_no_discrepancy() -> None:
    primary = [_candle("2500.00", source="primary")]
    secondary = [_candle("2500.05", source="secondary")]
    assert detect_discrepancies(primary, secondary) == []


def test_meaningful_divergence_is_flagged() -> None:
    primary = [_candle("2500.00", source="primary")]
    secondary = [_candle("2550.00", source="secondary")]  # ~200 bps off
    result = detect_discrepancies(primary, secondary, tolerance_bps=Decimal(50))
    assert len(result) == 1
    assert result[0].primary_close == Decimal("2500.00")
    assert result[0].secondary_close == Decimal("2550.00")
    assert result[0].divergence_bps > Decimal(50)


def test_candle_present_on_only_one_feed_is_not_a_discrepancy() -> None:
    primary = [_candle("2500.00", source="primary")]
    secondary: list[Candle] = []
    assert detect_discrepancies(primary, secondary) == []


def test_duplicate_candle_in_one_feed_fails_closed() -> None:
    primary = [_candle("2500.00", source="primary"), _candle("2500.00", source="primary")]
    secondary = [_candle("2500.00", source="secondary")]
    with pytest.raises(ValueError, match="duplicate candle"):
        detect_discrepancies(primary, secondary)


def test_negative_tolerance_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        detect_discrepancies([], [], tolerance_bps=Decimal(-1))
