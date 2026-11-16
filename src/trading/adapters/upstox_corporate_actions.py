"""Authenticated Upstox company-fundamentals corporate-action API client."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

from pydantic import Field

from trading.core.models import Contract

BASE_URL = "https://api.upstox.com/v2/fundamentals"
PARSER_VERSION = "1"


class UpstoxCorporateActionsError(RuntimeError):
    """Raised when the Upstox corporate-actions API cannot provide valid data."""


def _request(url: str, headers: dict[str, str]) -> bytes:
    request = Request(url, headers={"User-Agent": "tijori-research/1.0", **headers})
    try:
        opener = build_opener(_RejectRedirects())
        with opener.open(request, timeout=30) as response:
            return cast(bytes, response.read())
    except HTTPError as error:
        # Avoid echoing provider response bodies that could contain sensitive details.
        raise UpstoxCorporateActionsError(f"Upstox corporate-actions HTTP {error.code}") from error
    except URLError as error:
        raise UpstoxCorporateActionsError(
            f"Upstox corporate-actions transport error: {error.reason}"
        ) from error


class _RejectRedirects(HTTPRedirectHandler):
    """Never forward an authenticated corporate-action request to a redirect URL."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


class UpstoxCorporateAction(Contract):
    """Provider event with ordered details and ratio text left uninterpreted."""

    isin: str = Field(min_length=12, max_length=12)
    name: str = Field(min_length=1)
    effective_date: date
    ratio_text: str | None = None
    amount: Decimal | None = None
    details: tuple[tuple[str, str], ...] = ()
    source_ref: str = Field(min_length=1)


class UpstoxCorporateActionsSnapshot(Contract):
    """Parsed events and immutable provider response evidence for one ISIN."""

    isin: str = Field(min_length=12, max_length=12)
    source_ref: str = Field(min_length=1)
    retrieved_at_utc: datetime
    response_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    parser_version: str = Field(min_length=1)
    raw_response: bytes
    events: tuple[UpstoxCorporateAction, ...]


def _parse_date(value: object) -> date:
    text = str(value).strip()
    for pattern in ("%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    raise UpstoxCorporateActionsError("Upstox returned an unsupported corporate-action date")


def _parse_event(row: object, *, isin: str, source_ref: str) -> UpstoxCorporateAction:
    if not isinstance(row, dict):
        raise UpstoxCorporateActionsError("Upstox corporate-action entry is not an object")
    name = row.get("name")
    effective = row.get("expiry_date")
    if not isinstance(name, str) or not name.strip() or effective is None:
        raise UpstoxCorporateActionsError("Upstox corporate-action entry lacks name or date")
    raw_details = row.get("event_details", [])
    if not isinstance(raw_details, list):
        raise UpstoxCorporateActionsError("Upstox event_details is not a list")
    details: list[tuple[str, str]] = []
    for item in raw_details:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise UpstoxCorporateActionsError("Upstox event detail has an invalid shape")
        details.append((item["name"], str(item.get("value", ""))))

    ratio = row.get("ratio")
    if ratio is not None and not isinstance(ratio, str):
        ratio = str(ratio)
    amount_value = row.get("amount")
    try:
        amount = Decimal(str(amount_value)) if amount_value is not None else None
    except InvalidOperation as error:
        raise UpstoxCorporateActionsError("Upstox event amount is not numeric") from error

    return UpstoxCorporateAction(
        isin=isin,
        name=name.strip(),
        effective_date=_parse_date(effective),
        ratio_text=ratio,
        amount=amount,
        details=tuple(details),
        source_ref=source_ref,
    )


class UpstoxCorporateActionsClient:
    """Fetch actions by ISIN; requires an explicitly supplied current token."""

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        requester: Callable[[str, dict[str, str]], bytes] = _request,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        user_agent: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._requester = requester
        self._clock = clock
        self._user_agent = user_agent

    def fetch(self, isin: str, *, access_token: str) -> UpstoxCorporateActionsSnapshot:
        normalized_isin = isin.strip().upper()
        if len(normalized_isin) != 12 or not normalized_isin.isalnum():
            raise ValueError("ISIN must be a 12-character alphanumeric identifier")
        if not access_token.strip():
            raise ValueError("a current Upstox access token is required")
        source_ref = f"{self._base_url}/{quote(normalized_isin, safe='')}/corporate-actions"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        if self._user_agent:
            headers["User-Agent"] = self._user_agent
        try:
            raw_response = self._requester(source_ref, headers)
            retrieved_at = self._clock()
            if retrieved_at.tzinfo is None or retrieved_at.utcoffset() != timedelta(0):
                raise ValueError("corporate-action retrieval clock must return UTC-aware time")
            payload = json.loads(raw_response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise UpstoxCorporateActionsError("Upstox returned invalid JSON") from error
        if not isinstance(payload, dict) or payload.get("status") != "success":
            raise UpstoxCorporateActionsError("Upstox corporate-actions API reported failure")
        rows = payload.get("data")
        if not isinstance(rows, list):
            raise UpstoxCorporateActionsError("Upstox response data is not a list")
        events = tuple(
            _parse_event(row, isin=normalized_isin, source_ref=source_ref) for row in rows
        )
        return UpstoxCorporateActionsSnapshot(
            isin=normalized_isin,
            source_ref=source_ref,
            retrieved_at_utc=retrieved_at,
            response_sha256=sha256(raw_response).hexdigest(),
            parser_version=PARSER_VERSION,
            raw_response=raw_response,
            events=events,
        )
