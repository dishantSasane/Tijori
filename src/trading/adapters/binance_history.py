"""Token-free Binance public candle adapter (crypto + memecoin sleeves).

Why Binance REST via stdlib `urllib`, not `ccxt` (docs/MARKETS.md names ccxt
as the default crypto data source, but leaves "exchange choice" open):
Upstox's adapter (`upstox_history.py`) deliberately skips an SDK and talks
raw REST with stdlib `urllib`, so a crypto adapter that pulls from one
exchange gets no benefit from ccxt's multi-exchange normalization layer --
it would just be an extra dependency wrapping the same one JSON endpoint.
If a second exchange is ever added for cross-checking or redundancy, ccxt
becomes worth it; until then, consistency with the existing adapter wins.

Free vs. paid: `/api/v3/klines` (spot candles) is public, unauthenticated,
and free with no tier gate. There is no stated hard cutoff on how far back
history goes (checked api.binance.com/api/v3/exchangeInfo and the public
REST docs on 2026-11-15) -- in practice it runs back to each symbol's spot
listing date, which for most tokens is some point after 2017-2018 (Binance's
own launch). Nothing here requires a paid tier.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle

BASE_URL = "https://api.binance.com/api/v3/klines"

#: Binance's own hard cap on candles returned per request (verified
#: 2026-11-15 against the public REST docs).
MAX_CANDLES_PER_REQUEST = 1000

#: Default per-IP weight budget (api.binance.com/api/v3/exchangeInfo,
#: checked 2026-11-15): 6000 weight / minute. Each klines call costs weight 2,
#: so a caller can safely issue up to 3000 klines requests/minute; the
#: historical loader throttles well under that.
REQUEST_WEIGHT_PER_MINUTE = 6000
KLINES_REQUEST_WEIGHT = 2


class BinanceHistoryError(RuntimeError):
    """Raised when Binance returns a transport or API error."""


def _request(url: str, headers: dict[str, str]) -> bytes:
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed HTTPS base URL
            return cast(bytes, response.read())
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise BinanceHistoryError(f"Binance HTTP {error.code}: {body}") from error
    except URLError as error:
        raise BinanceHistoryError(f"Binance transport error: {error.reason}") from error


class BinanceHistoryClient:
    """Fetch public spot candles. No API key, no login flow, no SDK."""

    def __init__(
        self, *, base_url: str = BASE_URL, requester: Callable[..., bytes] = _request
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._requester = requester

    def fetch(
        self,
        binance_symbol: str,
        *,
        symbol: str,
        market: MarketId,
        timeframe: Timeframe,
        ingest_ts: datetime,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
        limit: int = MAX_CANDLES_PER_REQUEST,
    ) -> list[Candle]:
        if market not in (MarketId.CRYPTO, MarketId.MEMECOIN):
            raise ValueError(f"Binance adapter is crypto/memecoin only, got {market}")
        if limit < 1 or limit > MAX_CANDLES_PER_REQUEST:
            raise ValueError(f"limit must be in [1, {MAX_CANDLES_PER_REQUEST}]")
        params: dict[str, str | int] = {
            "symbol": binance_symbol,
            "interval": self._interval(timeframe),
            "limit": limit,
        }
        if start_time_ms is not None:
            params["startTime"] = start_time_ms
        if end_time_ms is not None:
            params["endTime"] = end_time_ms
        path = f"{self._base_url}?{urlencode(params)}"
        try:
            payload = json.loads(self._requester(path, {"Accept": "application/json"}).decode())
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise BinanceHistoryError("Binance returned invalid JSON") from error
        if not isinstance(payload, list):
            raise BinanceHistoryError(f"Binance API error: {payload}")
        return [
            self._candle(
                row, symbol=symbol, market=market, timeframe=timeframe, ingest_ts=ingest_ts
            )
            for row in payload
        ]

    @staticmethod
    def _interval(timeframe: Timeframe) -> str:
        if timeframe is Timeframe.D1:
            return "1d"
        if timeframe is Timeframe.M1:
            return "1m"
        if timeframe is Timeframe.M5:
            return "5m"
        if timeframe is Timeframe.M15:
            return "15m"
        if timeframe is Timeframe.H1:
            return "1h"
        raise ValueError(f"Binance timeframe unsupported: {timeframe}")

    @staticmethod
    def _candle(
        row: list[object],
        *,
        symbol: str,
        market: MarketId,
        timeframe: Timeframe,
        ingest_ts: datetime,
    ) -> Candle:
        if len(row) < 6:
            raise BinanceHistoryError("Binance candle row has fewer than six fields")
        open_ms = row[0]
        if not isinstance(open_ms, int):
            raise BinanceHistoryError("Binance candle open time is not an integer")
        timestamp = datetime.fromtimestamp(open_ms / 1000, tz=UTC)
        return Candle(
            market=market,
            symbol=symbol,
            timeframe=timeframe,
            ts_open_utc=timestamp,
            open=Decimal(str(row[1])),
            high=Decimal(str(row[2])),
            low=Decimal(str(row[3])),
            close=Decimal(str(row[4])),
            volume=Decimal(str(row[5])),
            source="binance",
            ingest_ts=ingest_ts,
        )
