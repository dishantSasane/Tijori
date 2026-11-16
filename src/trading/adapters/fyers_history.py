"""Fyers API v3 historical-candle adapter -- free, used only as a second
live-data source for cross-validation against the chosen primary feed
(`cross_validated_feed.py`), never as the sole source for a sleeve.

Request parameter names (`symbol`, `resolution`, `date_format`, `range_from`,
`range_to`) and the response's `candles`/`s` fields are confirmed against
Fyers' own published API-v3 parameter reference. The exact base URL/path
below (`api-t1.fyers.in/data/history`) and the `Authorization: "<app_id>:
<access_token>"` header format follow Fyers' documented v3 auth convention,
but this environment could not crawl the full REST reference page (JS app)
to byte-for-byte confirm the path during review -- **verify against a live
Fyers sandbox call before trusting it in production**; flagged, not silently
assumed correct.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pydantic import Field

from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle, Contract

BASE_URL = "https://api-t1.fyers.in/data/history"

_RESOLUTION_BY_TIMEFRAME: dict[Timeframe, str] = {
    Timeframe.M1: "1",
    Timeframe.M5: "5",
    Timeframe.M15: "15",
    Timeframe.H1: "60",
    Timeframe.D1: "D",
}


class FyersHistoryError(RuntimeError):
    """Raised when Fyers returns a transport or API error."""


class FyersHistorySnapshot(Contract):
    fyers_symbol: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    market: MarketId
    timeframe: Timeframe
    range_from: str = Field(min_length=1)
    range_to: str = Field(min_length=1)
    retrieved_at_utc: datetime
    response_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_response: bytes
    candles: tuple[Candle, ...]


def _request(url: str, headers: dict[str, str]) -> bytes:
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed HTTPS base URL
            return cast(bytes, response.read())
    except HTTPError as error:
        raise FyersHistoryError(f"Fyers HTTP {error.code}") from error
    except URLError as error:
        raise FyersHistoryError(f"Fyers transport error: {error.reason}") from error


class FyersHistoryClient:
    """Fetch Fyers v3 historical candles, used for cross-validation only."""

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        app_id: str,
        requester: Callable[[str, dict[str, str]], bytes] = _request,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        if not app_id.strip():
            raise ValueError("a Fyers app_id is required")
        self._base_url = base_url.rstrip("/")
        self._app_id = app_id
        self._requester = requester
        self._clock = clock

    def fetch(
        self,
        fyers_symbol: str,
        *,
        symbol: str,
        market: MarketId,
        timeframe: Timeframe,
        range_from: str,
        range_to: str,
        access_token: str,
        ingest_ts: datetime,
    ) -> list[Candle]:
        return list(
            self.fetch_snapshot(
                fyers_symbol,
                symbol=symbol,
                market=market,
                timeframe=timeframe,
                range_from=range_from,
                range_to=range_to,
                access_token=access_token,
                ingest_ts=ingest_ts,
            ).candles
        )

    def fetch_snapshot(
        self,
        fyers_symbol: str,
        *,
        symbol: str,
        market: MarketId,
        timeframe: Timeframe,
        range_from: str,
        range_to: str,
        access_token: str,
        ingest_ts: datetime,
    ) -> FyersHistorySnapshot:
        if timeframe not in _RESOLUTION_BY_TIMEFRAME:
            raise ValueError(f"Fyers timeframe unsupported: {timeframe}")
        if not access_token.strip():
            raise ValueError("a Fyers access token is required")
        params = {
            "symbol": fyers_symbol,
            "resolution": _RESOLUTION_BY_TIMEFRAME[timeframe],
            "date_format": "1",
            "range_from": range_from,
            "range_to": range_to,
            "cont_flag": "0",
        }
        url = f"{self._base_url}?{urlencode(params)}"
        headers = {
            "Accept": "application/json",
            "Authorization": f"{self._app_id}:{access_token}",
        }
        try:
            raw_response = self._requester(url, headers)
            retrieved_at = self._clock()
            if retrieved_at.tzinfo is None or retrieved_at.utcoffset() != timedelta(0):
                raise ValueError("Fyers retrieval clock must return UTC-aware time")
            payload = json.loads(raw_response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise FyersHistoryError("Fyers returned invalid JSON") from error
        if payload.get("s") != "ok":
            raise FyersHistoryError(f"Fyers API error: {payload}")
        rows = payload.get("candles", [])
        if not isinstance(rows, list):
            raise FyersHistoryError("Fyers response candles is not a list")
        candles = tuple(
            self._candle(
                row, symbol=symbol, market=market, timeframe=timeframe, ingest_ts=ingest_ts
            )
            for row in rows
        )
        return FyersHistorySnapshot(
            fyers_symbol=fyers_symbol,
            symbol=symbol,
            market=market,
            timeframe=timeframe,
            range_from=range_from,
            range_to=range_to,
            retrieved_at_utc=retrieved_at,
            response_sha256=sha256(raw_response).hexdigest(),
            raw_response=raw_response,
            candles=candles,
        )

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
            raise FyersHistoryError("Fyers candle row has fewer than six fields")
        timestamp = datetime.fromtimestamp(float(cast(float, row[0])), tz=UTC)
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
            source="fyers",
            ingest_ts=ingest_ts,
        )
