from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading.brain.context_cache import ContextCache
from trading.core.enums import BrainLabel
from trading.core.models import BrainVerdict

TS = datetime(2026, 1, 1, tzinfo=UTC)


def _verdict(signal_id: str) -> BrainVerdict:
    return BrainVerdict(
        signal_id=signal_id, label=BrainLabel.SUPPORT, size_multiplier=Decimal(1), created_ts=TS
    )


def test_cache_miss_returns_none():
    cache = ContextCache(ttl=timedelta(hours=1))
    assert cache.get("sig-1", "ctx", now=TS) is None


def test_cache_hit_returns_same_verdict():
    cache = ContextCache(ttl=timedelta(hours=1))
    v = _verdict("sig-1")
    cache.put("sig-1", "ctx", v, now=TS)
    assert cache.get("sig-1", "ctx", now=TS) == v


def test_cache_expires_after_ttl():
    cache = ContextCache(ttl=timedelta(hours=1))
    v = _verdict("sig-1")
    cache.put("sig-1", "ctx", v, now=TS)
    later = TS + timedelta(hours=2)
    assert cache.get("sig-1", "ctx", now=later) is None


def test_different_context_is_a_different_cache_entry():
    cache = ContextCache(ttl=timedelta(hours=1))
    v = _verdict("sig-1")
    cache.put("sig-1", "ctx-a", v, now=TS)
    assert cache.get("sig-1", "ctx-b", now=TS) is None


def test_different_signal_id_same_context_is_a_different_cache_entry():
    cache = ContextCache(ttl=timedelta(hours=1))
    v = _verdict("sig-1")
    cache.put("sig-1", "ctx", v, now=TS)
    assert cache.get("sig-2", "ctx", now=TS) is None
