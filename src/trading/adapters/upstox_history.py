"""Token-optional Upstox historical candle adapter.

This adapter deliberately does not implement OAuth or daily token renewal.
Callers may provide an already-issued daily access token; when omitted, the
request is sent without an Authorization header for endpoints that permit it.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from pydantic import Field

from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle, Contract

BASE_URL = "https://api.upstox.com/v3/historical-candle"


class UpstoxHistoryError(RuntimeError):
    """Raised when Upstox returns a transport or API error."""


class UpstoxHistorySnapshot(Contract):
    """Immutable exact response bytes plus parsed candles and request provenance."""

    instrument_key: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    market: MarketId
    timeframe: Timeframe
    from_date: str | None = None
    to_date: str
    retrieved_at_utc: datetime
    response_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_response: bytes
    candles: tuple[Candle, ...]


def _request(url: str, headers: dict[str, str]) -> bytes:
    request_headers = {"User-Agent": "tijori-research/1.0", **headers}
    request = Request(url, headers=request_headers, method="GET")
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed HTTPS base URL
            return cast(bytes, response.read())
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise UpstoxHistoryError(f"Upstox HTTP {error.code}: {body}") from error
    except URLError as error:
        raise UpstoxHistoryError(f"Upstox transport error: {error.reason}") from error


class UpstoxHistoryClient:
    """Fetch V3 historical/intraday candles without implementing login flow."""

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        requester: Callable[..., bytes] = _request,
        user_agent: str | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._requester = requester
        self._user_agent = user_agent
        self._clock = clock

    def fetch(
        self,
        instrument_key: str,
        *,
        symbol: str,
        market: MarketId,
        timeframe: Timeframe,
        to_date: str,
        ingest_ts: datetime,
        from_date: str | None = None,
        access_token: str | None = None,
    ) -> list[Candle]:
        return list(
            self.fetch_snapshot(
                instrument_key,
                symbol=symbol,
                market=market,
                timeframe=timeframe,
                to_date=to_date,
                ingest_ts=ingest_ts,
                from_date=from_date,
                access_token=access_token,
            ).candles
        )

    def fetch_snapshot(
        self,
        instrument_key: str,
        *,
        symbol: str,
        market: MarketId,
        timeframe: Timeframe,
        to_date: str,
        ingest_ts: datetime,
        from_date: str | None = None,
        access_token: str | None = None,
    ) -> UpstoxHistorySnapshot:
        """Fetch once and preserve exact bytes before parsing them."""
        unit, interval, is_intraday = self._path_parts(timeframe)
        encoded_key = quote(instrument_key, safe="")
        if is_intraday and from_date is None:
            path = f"{self._base_url}/intraday/{encoded_key}/{unit}/{interval}"
        else:
            path = f"{self._base_url}/{encoded_key}/{unit}/{interval}/{to_date}"
            if from_date is not None:
                path += f"/{from_date}"
        headers = {"Accept": "application/json"}
        if self._user_agent:
            headers["User-Agent"] = self._user_agent
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        try:
            raw_response = self._requester(path, headers)
            retrieved_at = self._clock()
            if retrieved_at.tzinfo is None or retrieved_at.utcoffset() != timedelta(0):
                raise ValueError("Upstox history retrieval clock must return UTC-aware time")
            payload = json.loads(raw_response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise UpstoxHistoryError("Upstox returned invalid JSON") from error
        if payload.get("status") != "success":
            raise UpstoxHistoryError(f"Upstox API error: {payload}")
        candles = payload.get("data", {}).get("candles", [])
        if not isinstance(candles, list):
            raise UpstoxHistoryError("Upstox response data.candles is not a list")
        candles = tuple(
            self._candle(
                row, symbol=symbol, market=market, timeframe=timeframe, ingest_ts=ingest_ts
            )
            for row in candles
        )
        return UpstoxHistorySnapshot(
            instrument_key=instrument_key,
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
    def _path_parts(timeframe: Timeframe) -> tuple[str, str, bool]:
        if timeframe is Timeframe.D1:
            return "days", "1", False
        if timeframe is Timeframe.M1:
            return "minutes", "1", True
        if timeframe is Timeframe.M5:
            return "minutes", "5", True
        if timeframe is Timeframe.M15:
            return "minutes", "15", True
        if timeframe is Timeframe.H1:
            return "hours", "1", True
        raise ValueError(f"Upstox timeframe unsupported: {timeframe}")

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
            raise UpstoxHistoryError("Upstox candle row has fewer than six fields")
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
            source="upstox",
            ingest_ts=ingest_ts,
        )
