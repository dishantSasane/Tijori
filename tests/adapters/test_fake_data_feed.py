from datetime import UTC, datetime
from decimal import Decimal

from trading.adapters.data_feed import FakeDataFeed
from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle, Tick


def test_poll_closed_candles_returns_and_clears() -> None:
    feed = FakeDataFeed()
    candle = Candle(
        market=MarketId.IN_EQUITY,
        symbol="RELIANCE",
        timeframe=Timeframe.D1,
        ts_open_utc=datetime(2026, 1, 1, tzinfo=UTC),
        open=Decimal(10),
        high=Decimal(11),
        low=Decimal(9),
        close=Decimal(10),
        volume=Decimal(100),
        source="fake",
    )
    feed.push_closed_candle(candle)
    assert feed.poll_closed_candles() == [candle]
    assert feed.poll_closed_candles() == []


def test_is_stale_true_when_no_tick_seen() -> None:
    feed = FakeDataFeed()
    assert feed.is_stale(
        MarketId.IN_EQUITY, "RELIANCE", as_of=datetime.now(UTC), max_age_seconds=30
    )


def test_is_stale_false_within_window() -> None:
    feed = FakeDataFeed()
    now = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    feed.push_tick(
        Tick(
            market=MarketId.IN_EQUITY,
            symbol="RELIANCE",
            ts_utc=now,
            price=Decimal(10),
            size=Decimal(1),
        )
    )
    later = datetime(2026, 1, 1, 10, 0, 10, tzinfo=UTC)
    assert not feed.is_stale(MarketId.IN_EQUITY, "RELIANCE", as_of=later, max_age_seconds=30)
