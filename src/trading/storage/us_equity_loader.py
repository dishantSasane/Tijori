"""Idempotent, resumable historical loader for Alpaca US equity bars.

Same resumability design as `crypto_loader.py`: progress is read back from
`CandleStore` (latest stored bar), never a separate checkpoint file.

Rate limiting: Alpaca's free "Basic" plan is 200 requests/minute (verified
live against docs.alpaca.markets on 2026-11-15 -- the pricing comparison
table states "200 API calls/min"). `REQUESTS_PER_MINUTE_BUDGET` below is set
well under that. Pagination differs from Binance/Upstox: Alpaca returns a
`next_page_token` when a single `start..end` window has more bars than
`limit` (max 10000 rows/page per the bars endpoint), so this loader follows
the token until exhausted before advancing its time cursor.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from trading.adapters.alpaca_history import Adjustment, AlpacaHistoryClient
from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle
from trading.storage.candles import CandleStore

#: Conservative self-throttle, well under Alpaca's 200 req/min free-tier cap.
REQUESTS_PER_MINUTE_BUDGET = 150

_TIMEFRAME_DURATIONS: dict[Timeframe, timedelta] = {
    Timeframe.M1: timedelta(minutes=1),
    Timeframe.M5: timedelta(minutes=5),
    Timeframe.M15: timedelta(minutes=15),
    Timeframe.H1: timedelta(hours=1),
    Timeframe.D1: timedelta(days=1),
}


def load_history(
    client: AlpacaHistoryClient,
    store: CandleStore,
    *,
    alpaca_symbol: str,
    symbol: str,
    market: MarketId,
    timeframe: Timeframe,
    start: datetime,
    end: datetime,
    adjustment: Adjustment = "raw",
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Backfill `[start, end)` into `store`, resuming from whatever is already
    stored and following Alpaca's `next_page_token` pagination. Returns the
    number of newly inserted candles.
    """
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("start/end must be timezone-aware UTC")
    step = _TIMEFRAME_DURATIONS[timeframe]

    existing = store.query(market, symbol, timeframe, start=start, end=end)
    cursor = max((c.ts_open_utc + step for c in existing), default=start)

    inserted = 0
    seconds_between_requests = 60.0 / REQUESTS_PER_MINUTE_BUDGET
    page_token: str | None = None
    while cursor < end:
        candles: list[Candle]
        candles, page_token = client.fetch(
            alpaca_symbol,
            symbol=symbol,
            market=market,
            timeframe=timeframe,
            start=cursor,
            end=end,
            ingest_ts=clock(),
            adjustment=adjustment,
            page_token=page_token,
        )
        if not candles:
            break
        inserted += store.append(candles)
        if page_token is None:
            cursor = candles[-1].ts_open_utc + step
        sleep(seconds_between_requests)
        if page_token is None and cursor >= end:
            break
    return inserted
