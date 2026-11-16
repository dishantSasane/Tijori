"""Angel One SmartAPI historical-candle adapter -- free, used only as a
second live-data source for cross-validation against the chosen primary
feed (`cross_validated_feed.py`), never as the sole source for a sleeve.

Endpoint/header shapes below follow Angel One's published `getCandleData`
request parameters (`exchange`, `symboltoken`, `interval`, `fromdate`,
`todate`) and SmartAPI's documented REST conventions (JWT bearer auth plus
the `X-PrivateKey`/`X-UserType`/`X-SourceID` headers SmartAPI requires on
every authenticated call). SmartAPI's own docs are a JS-rendered app that
this environment could not crawl to the byte-for-byte endpoint path during
review -- **verify this adapter's `BASE_URL`/`HISTORY_PATH`/header names
against a live SmartAPI sandbox call before trusting it in production**;
this is flagged, not silently assumed correct.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import Field

from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle, Contract

BASE_URL = "https://apiconnect.angelbroking.com"
HISTORY_PATH = "/rest/secure/angelbroking/historical/v1/getCandleData"

_INTERVAL_BY_TIMEFRAME: dict[Timeframe, str] = {
    Timeframe.M1: "ONE_MINUTE",
    Timeframe.M5: "FIVE_MINUTE",
    Timeframe.M15: "FIFTEEN_MINUTE",
    Timeframe.H1: "ONE_HOUR",
    Timeframe.D1: "ONE_DAY",
}


class AngelOneHistoryError(RuntimeError):
    """Raised when SmartAPI returns a transport or API error."""


class AngelOneHistorySnapshot(Contract):
    instrument_token: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    market: MarketId
    timeframe: Timeframe
    from_date: str = Field(min_length=1)
    to_date: str = Field(min_length=1)
    retrieved_at_utc: datetime
    response_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_response: bytes
    candles: tuple[Candle, ...]


def _request(url: str, headers: dict[str, str], body: bytes) -> bytes:
    request = Request(url, data=body, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed HTTPS base URL
            return cast(bytes, response.read())
    except HTTPError as error:
        raise AngelOneHistoryError(f"SmartAPI HTTP {error.code}") from error
    except URLError as error:
        raise AngelOneHistoryError(f"SmartAPI transport error: {error.reason}") from error


class AngelOneHistoryClient:
    """Fetch SmartAPI historical candles, used for cross-validation only."""

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        api_key: str,
        requester: Callable[[str, dict[str, str], bytes], bytes] = _request,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        if not api_key.strip():
            raise ValueError("an Angel One API key (X-PrivateKey) is required")
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._requester = requester
        self._clock = clock

    def fetch(
        self,
        exchange_symbol_token: str,
        *,
        symbol: str,
        market: MarketId,
        timeframe: Timeframe,
        exchange: str,
        from_date: str,
        to_date: str,
        access_token: str,
        ingest_ts: datetime,
    ) -> list[Candle]:
        return list(
            self.fetch_snapshot(
                exchange_symbol_token,
                symbol=symbol,
                market=market,
                timeframe=timeframe,
                exchange=exchange,
                from_date=from_date,
                to_date=to_date,
                access_token=access_token,
                ingest_ts=ingest_ts,
            ).candles
        )

    def fetch_snapshot(
        self,
        exchange_symbol_token: str,
        *,
        symbol: str,
        market: MarketId,
        timeframe: Timeframe,
        exchange: str,
        from_date: str,
        to_date: str,
        access_token: str,
        ingest_ts: datetime,
    ) -> AngelOneHistorySnapshot:
        if timeframe not in _INTERVAL_BY_TIMEFRAME:
            raise ValueError(f"Angel One timeframe unsupported: {timeframe}")
        if not access_token.strip():
            raise ValueError("an Angel One session access token is required")
        payload = {
            "exchange": exchange,
            "symboltoken": exchange_symbol_token,
            "interval": _INTERVAL_BY_TIMEFRAME[timeframe],
            "fromdate": from_date,
            "todate": to_date,
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "X-PrivateKey": self._api_key,
            "X-UserType": "USER",
            "X-SourceID": "WEB",
        }
        try:
            raw_response = self._requester(f"{self._base_url}{HISTORY_PATH}", headers, body)
            retrieved_at = self._clock()
            if retrieved_at.tzinfo is None or retrieved_at.utcoffset() != timedelta(0):
                raise ValueError("Angel One retrieval clock must return UTC-aware time")
            response_payload = json.loads(raw_response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AngelOneHistoryError("SmartAPI returned invalid JSON") from error
        if not response_payload.get("status"):
            raise AngelOneHistoryError(f"SmartAPI API error: {response_payload}")
        rows = response_payload.get("data", [])
        if not isinstance(rows, list):
            raise AngelOneHistoryError("SmartAPI response data is not a list")
        candles = tuple(
            self._candle(
                row, symbol=symbol, market=market, timeframe=timeframe, ingest_ts=ingest_ts
            )
            for row in rows
        )
        return AngelOneHistorySnapshot(
            instrument_token=exchange_symbol_token,
            symbol=symbol,
            market=market,
            timeframe=timeframe,
            from_date=from_date,
            to_date=to_date,
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
            raise AngelOneHistoryError("SmartAPI candle row has fewer than six fields")
        timestamp = datetime.fromisoformat(str(row[0])).astimezone(UTC)
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
            source="angelone",
            ingest_ts=ingest_ts,
        )
