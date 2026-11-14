"""Token-optional Upstox historical candle adapter.

This adapter deliberately does not implement OAuth or daily token renewal.
Callers may provide an already-issued daily access token; when omitted, the
request is sent without an Authorization header for endpoints that permit it.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle

BASE_URL = "https://api.upstox.com/v3/historical-candle"


class UpstoxHistoryError(RuntimeError):
    """Raised when Upstox returns a transport or API error."""


def _request(url: str, headers: dict[str, str]) -> bytes:
    request = Request(url, headers=headers, method="GET")
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
        self, *, base_url: str = BASE_URL, requester: Callable[..., bytes] = _request
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._requester = requester

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
        unit, interval, is_intraday = self._path_parts(timeframe)
        encoded_key = quote(instrument_key, safe="")
        if is_intraday:
            path = f"{self._base_url}/intraday/{encoded_key}/{unit}/{interval}"
        else:
            path = f"{self._base_url}/{encoded_key}/{unit}/{interval}/{to_date}"
            if from_date is not None:
                path += f"/{from_date}"
        headers = {"Accept": "application/json"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        try:
            payload = json.loads(self._requester(path, headers).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise UpstoxHistoryError("Upstox returned invalid JSON") from error
        if payload.get("status") != "success":
            raise UpstoxHistoryError(f"Upstox API error: {payload}")
        candles = payload.get("data", {}).get("candles", [])
        if not isinstance(candles, list):
            raise UpstoxHistoryError("Upstox response data.candles is not a list")
        return [
            self._candle(
                row, symbol=symbol, market=market, timeframe=timeframe, ingest_ts=ingest_ts
            )
            for row in candles
        ]

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
