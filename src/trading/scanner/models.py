"""Scanner contracts.

A "scanner idea" is not a Signal (core/models.py): it never reaches the risk
engine or a broker. It is a research-grade suggestion for a human to look
at on the Stocks page -- "this symbol passed today's filters, here is a
rough target and a level at which the idea looks wrong." Nothing here places
an order; see docs/BUILD_ORDER.md P4 and AGENTS.md §4.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import Field

from trading.core.enums import MarketId
from trading.core.models import Contract


class ScannerIdea(Contract):
    """One symbol's result from one day's scan."""

    symbol: str = Field(min_length=1)
    market: MarketId
    as_of: date
    last_close: Decimal = Field(gt=0)
    avg_turnover: Decimal = Field(ge=0)
    rank_score: float
    target_price: Decimal = Field(gt=0)
    reconsider_price: Decimal = Field(gt=0)
    reasons: tuple[str, ...] = Field(min_length=1)
