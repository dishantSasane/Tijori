"""Point-in-time split and bonus adjustment for raw daily candles.

The caller must establish that input candles are raw, unadjusted prices. The
Upstox historical API documentation currently does not state its adjustment
basis; never apply this transform to Upstox data until that is verified.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import Field, model_validator

from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle, Contract

INDIA_TIMEZONE = ZoneInfo("Asia/Kolkata")


class ShareAdjustment(Contract):
    """A sourced split or bonus issue, expressed as new shares per old share."""

    action_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    revision: int = Field(ge=1)
    market: MarketId
    symbol: str = Field(min_length=1)
    kind: Literal["split", "bonus"]
    published_date: date
    effective_date: date
    new_shares_per_old_share: Decimal = Field(gt=0)
    source_ref: str = Field(min_length=1)

    @model_validator(mode="after")
    def _ratio_must_change_share_count(self) -> ShareAdjustment:
        if self.market is not MarketId.IN_EQUITY:
            raise ValueError("P1 share adjustments currently support India equities only")
        if self.new_shares_per_old_share == Decimal("1"):
            raise ValueError("share adjustment ratio must differ from 1")
        if self.kind == "bonus" and self.new_shares_per_old_share <= Decimal("1"):
            raise ValueError("bonus issues must increase shares per old share")
        return self


def adjust_for_share_actions(
    candles: Iterable[Candle],
    actions: Iterable[ShareAdjustment],
    *,
    as_of: date,
) -> list[Candle]:
    """Return candles adjusted for known splits/bonuses as of an India date.

    For an action published and effective by ``as_of``, bars from earlier
    sessions are divided by the share ratio and volume is multiplied by it.
    Bars on the effective session or later remain at their traded values.
    Future/unpublished actions are ignored, so a historical replay must call
    this with its own as-of date.

    The original immutable candles are retained. Adjusted bars carry the
    cumulative price multiplier in ``adj_factor``. Input must be unadjusted
    daily candles; a marked candle or another timeframe fails closed.
    Dividends, rights issues, mergers, and other events are intentionally not
    inferred or handled here.
    """
    candle_list = list(candles)
    action_list = list(actions)
    seen_ids: set[str] = set()
    versions_by_event: dict[str, list[ShareAdjustment]] = {}
    for action in action_list:
        if action.action_id in seen_ids:
            raise ValueError(f"duplicate corporate action id: {action.action_id}")
        seen_ids.add(action.action_id)
        versions_by_event.setdefault(action.event_id, []).append(action)

    selected_actions: list[ShareAdjustment] = []
    for event_id, versions in versions_by_event.items():
        ordered_versions = sorted(versions, key=lambda item: item.revision)
        if len({item.revision for item in ordered_versions}) != len(ordered_versions):
            raise ValueError(f"duplicate corporate action revision for event: {event_id}")
        if any(
            earlier.published_date >= later.published_date
            for earlier, later in zip(ordered_versions, ordered_versions[1:], strict=False)
        ):
            raise ValueError(
                f"corporate action revisions are not chronologically published: {event_id}"
            )
        known_versions = [item for item in ordered_versions if item.published_date <= as_of]
        if known_versions:
            selected_actions.append(known_versions[-1])

    adjusted: list[Candle] = []
    for candle in candle_list:
        if candle.timeframe is not Timeframe.D1:
            raise ValueError("P1 corporate-action adjustment supports daily candles only")
        if candle.adj_factor is not None:
            raise ValueError(
                f"candle {candle.symbol} at {candle.ts_open_utc.isoformat()} is already adjusted"
            )
        session_date = candle.ts_open_utc.astimezone(INDIA_TIMEZONE).date()
        price_factor = Decimal("1")
        for action in selected_actions:
            if (
                action.market == candle.market
                and action.symbol == candle.symbol
                and session_date < action.effective_date <= as_of
            ):
                price_factor /= action.new_shares_per_old_share

        if price_factor == Decimal("1"):
            adjusted.append(candle)
            continue
        adjusted.append(
            Candle.model_validate(
                {
                    **candle.model_dump(),
                    "open": candle.open * price_factor,
                    "high": candle.high * price_factor,
                    "low": candle.low * price_factor,
                    "close": candle.close * price_factor,
                    "volume": candle.volume / price_factor,
                    "adj_factor": price_factor,
                }
            )
        )
    return adjusted
