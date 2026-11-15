"""Authenticated Upstox company-fundamentals corporate-action API client."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from pydantic import Field

from trading.core.models import Contract

BASE_URL = "https://api.upstox.com/v2/fundamentals"


class UpstoxCorporateActionsError(RuntimeError):
    """Raised when the Upstox corporate-actions API cannot provide valid data."""


def _request(url: str, headers: dict[str, str]) -> bytes:
    request = Request(url, headers={"User-Agent": "tijori-research/1.0", **headers})
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed HTTPS base URL
            return cast(bytes, response.read())
    except HTTPError as error:
        # Avoid echoing provider response bodies that could contain sensitive details.
        raise UpstoxCorporateActionsError(f"Upstox corporate-actions HTTP {error.code}") from error
    except URLError as error:
        raise UpstoxCorporateActionsError(
            f"Upstox corporate-actions transport error: {error.reason}"
        ) from error


class UpstoxCorporateAction(Contract):
    """Provider event with its reported ratio preserved without interpretation."""

    isin: str = Field(min_length=12, max_length=12)
    name: str = Field(min_length=1)
    effective_date: date
    ratio_text: str | None = None
    amount: Decimal | None = None
    details: dict[str, str] = Field(default_factory=dict)
    source_ref: str = Field(min_length=1)


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
    details: dict[str, str] = {}
    for item in raw_details:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise UpstoxCorporateActionsError("Upstox event detail has an invalid shape")
        details[item["name"]] = str(item.get("value", ""))

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
        details=details,
        source_ref=source_ref,
    )


class UpstoxCorporateActionsClient:
    """Fetch actions by ISIN; requires an explicitly supplied current token."""

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        requester: Callable[[str, dict[str, str]], bytes] = _request,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._requester = requester

    def fetch(self, isin: str, *, access_token: str) -> list[UpstoxCorporateAction]:
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
        try:
            payload = json.loads(self._requester(source_ref, headers).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise UpstoxCorporateActionsError("Upstox returned invalid JSON") from error
        if not isinstance(payload, dict) or payload.get("status") != "success":
            raise UpstoxCorporateActionsError("Upstox corporate-actions API reported failure")
        rows = payload.get("data")
        if not isinstance(rows, list):
            raise UpstoxCorporateActionsError("Upstox response data is not a list")
        return [_parse_event(row, isin=normalized_isin, source_ref=source_ref) for row in rows]
