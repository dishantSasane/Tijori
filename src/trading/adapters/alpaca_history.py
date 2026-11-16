"""Key-required Alpaca historical bars adapter (US equities, IEX feed).

Free vs. paid (verified against docs.alpaca.markets on 2026-11-15 via live
WebFetch, not just the dated note in docs/MARKETS.md): Alpaca's free market
data plan ("Basic", bundled with every paper/live account) gives IEX-feed
bars, 200 API calls/minute, 7+ years of history, and a free corporate-actions
endpoint. Unlike Binance (`binance_history.py`, no key at all) or Upstox
(`upstox_history.py`, token optional for some endpoints), Alpaca's bars
endpoint requires an API key *pair* (key id + secret) on every request, even
on the free tier -- there is no anonymous/public path. Obtaining the pair is
free (sign up for a paper account); this adapter does not blur "free" with
"free after you register for a key".

Raw vs. adjusted -- the doc note in docs/MARKETS.md said Alpaca "provides
split/dividend-adjusted bars"; live verification shows that is only true if
the caller passes `adjustment=all` (or `split`/`dividend`). The endpoint's
own default is `adjustment=raw` (unadjusted). This adapter defaults to
`"raw"` to match Alpaca's own default and make the basis explicit at the
call site -- callers that want Alpaca's own adjustment must opt in with
`adjustment="all"`. `trading.storage.us_equity_corporate_actions` provides an
independent adjustment layer for when raw bars are fetched, built from
Alpaca's free Corporate Actions endpoint.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle

BASE_URL = "https://data.alpaca.markets/v2/stocks/bars"

#: Verified 2026-11-15 (docs.alpaca.markets pricing page): free "Basic" plan.
FREE_TIER_REQUESTS_PER_MINUTE = 200
FREE_TIER_HISTORY_YEARS = 7

Adjustment = Literal["raw", "split", "dividend", "all"]


class AlpacaHistoryError(RuntimeError):
    """Raised when Alpaca returns a transport or API error."""


def _request(url: str, headers: dict[str, str]) -> bytes:
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed HTTPS base URL
            return cast(bytes, response.read())
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise AlpacaHistoryError(f"Alpaca HTTP {error.code}: {body}") from error
    except URLError as error:
        raise AlpacaHistoryError(f"Alpaca transport error: {error.reason}") from error


class AlpacaHistoryClient:
    """Fetch IEX-feed stock bars. Requires a free key-id/secret pair -- unlike
    Binance's fully anonymous endpoint, there is no keyless path here.
    """

    def __init__(
        self,
        *,
        key_id: str,
        secret_key: str,
        base_url: str = BASE_URL,
        requester: Callable[..., bytes] = _request,
    ) -> None:
        if not key_id or not secret_key:
            raise ValueError("Alpaca requires a non-empty key_id and secret_key (free to obtain)")
        self._key_id = key_id
        self._secret_key = secret_key
        self._base_url = base_url.rstrip("/")
        self._requester = requester

    def fetch(
        self,
        alpaca_symbol: str,
        *,
        symbol: str,
        market: MarketId,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        ingest_ts: datetime,
        adjustment: Adjustment = "raw",
        feed: str = "iex",
        limit: int = 10000,
        page_token: str | None = None,
    ) -> tuple[list[Candle], str | None]:
        """Fetch one page of bars. Returns (candles, next_page_token)."""
        if market is not MarketId.US_EQUITY:
            raise ValueError(f"Alpaca adapter is US equities only, got {market}")
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("start/end must be timezone-aware UTC")
        params: dict[str, str | int] = {
            "symbols": alpaca_symbol,
            "timeframe": self._timeframe(timeframe),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "adjustment": adjustment,
            "feed": feed,
            "limit": limit,
        }
        if page_token:
            params["page_token"] = page_token
        path = f"{self._base_url}?{urlencode(params)}"
        headers = {
            "Accept": "application/json",
            "APCA-API-KEY-ID": self._key_id,
            "APCA-API-SECRET-KEY": self._secret_key,
        }
        try:
            payload = json.loads(self._requester(path, headers).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AlpacaHistoryError("Alpaca returned invalid JSON") from error
        if "bars" not in payload:
            raise AlpacaHistoryError(f"Alpaca API error: {payload}")
        rows = payload["bars"].get(alpaca_symbol, [])
        if not isinstance(rows, list):
            raise AlpacaHistoryError("Alpaca response bars entry is not a list")
        candles = [
            self._candle(
                row, symbol=symbol, market=market, timeframe=timeframe, ingest_ts=ingest_ts
            )
            for row in rows
        ]
        return candles, payload.get("next_page_token")

    @staticmethod
    def _timeframe(timeframe: Timeframe) -> str:
        if timeframe is Timeframe.D1:
            return "1Day"
        if timeframe is Timeframe.M1:
            return "1Min"
        if timeframe is Timeframe.M5:
            return "5Min"
        if timeframe is Timeframe.M15:
            return "15Min"
        if timeframe is Timeframe.H1:
            return "1Hour"
        raise ValueError(f"Alpaca timeframe unsupported: {timeframe}")

    @staticmethod
    def _candle(
        row: dict[str, object],
        *,
        symbol: str,
        market: MarketId,
        timeframe: Timeframe,
        ingest_ts: datetime,
    ) -> Candle:
        try:
            timestamp = datetime.fromisoformat(str(row["t"])).astimezone(UTC)
            return Candle(
                market=market,
                symbol=symbol,
                timeframe=timeframe,
                ts_open_utc=timestamp,
                open=Decimal(str(row["o"])),
                high=Decimal(str(row["h"])),
                low=Decimal(str(row["l"])),
                close=Decimal(str(row["c"])),
                volume=Decimal(str(row["v"])),
                source="alpaca",
                ingest_ts=ingest_ts,
            )
        except KeyError as error:
            raise AlpacaHistoryError(f"Alpaca bar row missing field: {error}") from error
