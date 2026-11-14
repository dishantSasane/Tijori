from datetime import UTC, datetime
from decimal import Decimal

from trading.adapters.llm_provider import FakeLLMProvider, default_absent_verdict
from trading.adapters.news_feed import FakeNewsFeed, NewsItem
from trading.core.enums import BrainLabel, MarketId, OrderSide, Timeframe
from trading.core.models import BrainVerdict, Signal

TS = datetime(2026, 1, 1, tzinfo=UTC)


def _signal() -> Signal:
    return Signal(
        market=MarketId.IN_EQUITY,
        symbol="RELIANCE",
        timeframe=Timeframe.D1,
        strategy_id="t1_donchian",
        strategy_version="v1",
        side=OrderSide.BUY,
        entry_ref=Decimal(100),
        stop=Decimal(95),
        bar_ts_utc=TS,
        created_ts=TS,
    )


def test_fake_llm_provider_returns_none_when_configured_absent() -> None:
    provider = FakeLLMProvider(verdict=None)
    assert provider.get_verdict(_signal(), context="") is None


def test_fake_llm_provider_attaches_signal_id() -> None:
    verdict = BrainVerdict(
        signal_id="placeholder",
        label=BrainLabel.SUPPORT,
        size_multiplier=Decimal(1),
        created_ts=TS,
    )
    provider = FakeLLMProvider(verdict=verdict)
    signal = _signal()
    result = provider.get_verdict(signal, context="")
    assert result is not None
    assert result.signal_id == signal.id


def test_default_absent_verdict_is_neutral_full_size() -> None:
    verdict = default_absent_verdict("sig-1", now=TS)
    assert verdict.label == BrainLabel.NEUTRAL
    assert verdict.size_multiplier == Decimal(1)


def test_fake_news_feed_filters_by_time() -> None:
    old = NewsItem(ts_utc=datetime(2026, 1, 1, tzinfo=UTC), source="x", headline="old")
    new = NewsItem(ts_utc=datetime(2026, 1, 2, tzinfo=UTC), source="x", headline="new")
    feed = FakeNewsFeed([old, new])
    result = feed.fetch_since(datetime(2026, 1, 1, 12, tzinfo=UTC))
    assert result == [new]
