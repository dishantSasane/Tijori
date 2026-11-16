"""Shared context cache (docs/BRAIN_AND_COSTS.md §5: "no repeated calls for
the same unchanged signal"). Keyed by a hash of the exact prompt content, so
two signals that happen to produce identical context (same symbol, same
indicators, same headlines) share one call -- no rate-limit bookkeeping
beyond that, per owner's YAGNI instruction. In-process dict is enough for a
single trading process; a restart loses the cache, which is safe (it only
ever avoids *duplicate* calls, never changes correctness).
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta

from trading.core.models import BrainVerdict


class ContextCache:
    def __init__(self, ttl: timedelta) -> None:
        self._ttl = ttl
        self._store: dict[str, tuple[datetime, BrainVerdict]] = {}

    @staticmethod
    def key(signal_id: str, context: str) -> str:
        # signal_id included so a cache hit still returns a verdict that
        # carries the asking signal's own id (BrainVerdict.signal_id must
        # match the request, per docs/BRAIN_AND_COSTS.md §3).
        digest = hashlib.sha256(context.encode("utf-8")).hexdigest()
        return f"{digest}:{signal_id}"

    def get(self, signal_id: str, context: str, *, now: datetime) -> BrainVerdict | None:
        entry = self._store.get(self.key(signal_id, context))
        if entry is None:
            return None
        cached_at, verdict = entry
        if now - cached_at > self._ttl:
            return None
        return verdict

    def put(self, signal_id: str, context: str, verdict: BrainVerdict, *, now: datetime) -> None:
        self._store[self.key(signal_id, context)] = (now, verdict)
