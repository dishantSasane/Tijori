"""Idempotent, resumable historical loader for Binance candles.

Resumability: progress is "how far we've stored", read back from
`CandleStore` itself rather than separate bookkeeping -- the loader always
asks the store for the latest stored bar and resumes from there, so a crash
or restart just re-asks the same question (no separate checkpoint file to
drift out of sync, and `CandleStore.append` already de-dupes exact repeats
and fails closed on a changed value for the same key).

Rate limiting: Binance's public REST default IP budget is 6000 request-weight
per minute, and `/api/v3/klines` costs weight 2 (verified against
api.binance.com/api/v3/exchangeInfo and the public REST docs, 2026-11-15) --
i.e. up to 3000 klines calls/minute. `REQUESTS_PER_MINUTE_BUDGET` below is
set far under that ceiling; this loader is for backfilling history, not
racing the limit.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from trading.adapters.binance_history import MAX_CANDLES_PER_REQUEST, BinanceHistoryClient
from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle
from trading.storage.candles import CandleStore

#: Conservative self-throttle, well under Binance's 3000 klines-calls/minute
#: ceiling (see module docstring) -- the loader is not latency-sensitive.
REQUESTS_PER_MINUTE_BUDGET = 60

_TIMEFRAME_DURATIONS: dict[Timeframe, timedelta] = {
    Timeframe.M1: timedelta(minutes=1),
    Timeframe.M5: timedelta(minutes=5),
    Timeframe.M15: timedelta(minutes=15),
    Timeframe.H1: timedelta(hours=1),
    Timeframe.D1: timedelta(days=1),
}


def load_history(
    client: BinanceHistoryClient,
    store: CandleStore,
    *,
    binance_symbol: str,
    symbol: str,
    market: MarketId,
    timeframe: Timeframe,
    start: datetime,
    end: datetime,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Backfill `[start, end)` into `store`, resuming from whatever is already
    stored and paginating in `MAX_CANDLES_PER_REQUEST`-sized pages. Returns
    the number of newly inserted candles.
    """
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("start/end must be timezone-aware UTC")
    step = _TIMEFRAME_DURATIONS[timeframe]

    existing = store.query(market, symbol, timeframe, start=start, end=end)
    cursor = max((c.ts_open_utc + step for c in existing), default=start)

    inserted = 0
    seconds_between_requests = 60.0 / REQUESTS_PER_MINUTE_BUDGET
    while cursor < end:
        candles: list[Candle] = client.fetch(
            binance_symbol,
            symbol=symbol,
            market=market,
            timeframe=timeframe,
            ingest_ts=clock(),
            start_time_ms=int(cursor.timestamp() * 1000),
            end_time_ms=int(end.timestamp() * 1000) - 1,
            limit=MAX_CANDLES_PER_REQUEST,
        )
        if not candles:
            break
        inserted += store.append(candles)
        cursor = candles[-1].ts_open_utc + step
        if len(candles) < MAX_CANDLES_PER_REQUEST:
            break
        sleep(seconds_between_requests)
    return inserted
