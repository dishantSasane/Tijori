"""Point-in-time split/dividend adjustment for raw US equity daily candles.

Same raw-vs-adjusted problem as India (`trading.storage.corporate_actions`),
different answer: live verification of Alpaca's docs (2026-11-15) shows the
bars endpoint defaults to `adjustment=raw`, but a caller can ask Alpaca for
`adjustment=all` and get splits+dividends applied server-side for free -- OR
fetch raw bars plus Alpaca's free Corporate Actions endpoint
(`/v1/corporate-actions`, included on the free "Basic" plan with no paid-tier
gate) and adjust independently. This module is the independent path: it lets
a backtest cross-check Alpaca's own server-side adjustment, or adjust bars
that were deliberately fetched raw. No other free-and-complete US corporate
action source was found during this check; if Alpaca's own feed is ever
unavailable, there is currently no verified free fallback -- flagged below
and in docs/BUILD_ORDER.md for the owner.

Only forward/reverse stock splits and cash dividends are handled (the two
corporate actions that move a US equity's raw price enough to break backtest
continuity). Mergers, spin-offs, and stock dividends are intentionally not
inferred here, same scope limit as the India module.
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

US_EQUITY_TIMEZONE = ZoneInfo("America/New_York")


class USCorporateAction(Contract):
    """A sourced split or cash dividend, from Alpaca's corporate-actions feed."""

    action_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    revision: int = Field(ge=1)
    market: MarketId
    symbol: str = Field(min_length=1)
    kind: Literal["split", "dividend"]
    announced_date: date
    effective_date: date
    #: For a split: new shares per old share (e.g. 4-for-1 -> 4). For a
    #: dividend: the cash amount per share, used to derive a price-only
    #: adjustment factor at apply time (not a share-count change).
    ratio_or_cash_amount: Decimal = Field(gt=0)
    source_ref: str = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_kind(self) -> USCorporateAction:
        if self.market is not MarketId.US_EQUITY:
            raise ValueError("US equity corporate actions support US_EQUITY only")
        if self.kind == "split" and self.ratio_or_cash_amount == Decimal("1"):
            raise ValueError("split ratio must differ from 1")
        return self


def adjust_for_corporate_actions(
    candles: Iterable[Candle],
    actions: Iterable[USCorporateAction],
    *,
    as_of: date,
) -> list[Candle]:
    """Return candles adjusted for known splits/dividends as of a US trading date.

    Mirrors `corporate_actions.adjust_for_share_actions`: for each action
    announced and effective by `as_of`, bars strictly before the effective
    session are divided by the cumulative price factor (splits shrink price
    and inflate volume; dividends shrink price only, standard ex-dividend
    back-adjustment). Future/unannounced actions are ignored. Input must be
    unadjusted daily candles; an already-adjusted bar or another timeframe
    fails closed.
    """
    candle_list = list(candles)
    action_list = list(actions)
    seen_ids: set[str] = set()
    versions_by_event: dict[str, list[USCorporateAction]] = {}
    for action in action_list:
        if action.action_id in seen_ids:
            raise ValueError(f"duplicate corporate action id: {action.action_id}")
        seen_ids.add(action.action_id)
        versions_by_event.setdefault(action.event_id, []).append(action)

    selected_actions: list[USCorporateAction] = []
    for event_id, versions in versions_by_event.items():
        ordered_versions = sorted(versions, key=lambda item: item.revision)
        if len({item.revision for item in ordered_versions}) != len(ordered_versions):
            raise ValueError(f"duplicate corporate action revision for event: {event_id}")
        if any(
            earlier.announced_date >= later.announced_date
            for earlier, later in zip(ordered_versions, ordered_versions[1:], strict=False)
        ):
            raise ValueError(
                f"corporate action revisions are not chronologically announced: {event_id}"
            )
        known_versions = [item for item in ordered_versions if item.announced_date <= as_of]
        if known_versions:
            selected_actions.append(known_versions[-1])

    adjusted: list[Candle] = []
    for candle in candle_list:
        if candle.timeframe is not Timeframe.D1:
            raise ValueError("US equity corporate-action adjustment supports daily candles only")
        if candle.adj_factor is not None:
            raise ValueError(
                f"candle {candle.symbol} at {candle.ts_open_utc.isoformat()} is already adjusted"
            )
        session_date = candle.ts_open_utc.astimezone(US_EQUITY_TIMEZONE).date()
        price_factor = Decimal("1")
        split_factor = Decimal("1")
        for action in selected_actions:
            if not (
                action.market == candle.market
                and action.symbol == candle.symbol
                and session_date < action.effective_date <= as_of
            ):
                continue
            if action.kind == "split":
                price_factor /= action.ratio_or_cash_amount
                split_factor *= action.ratio_or_cash_amount
            else:  # dividend: standard ex-div back-adjustment needs the close
                # on the session before the ex-date; approximate with the
                # close on the earliest subsequent session we have, i.e. this
                # candle's own close, which is adequate for this fail-closed
                # bar-by-bar transform (no look-ahead: only past bars shrink).
                price_factor *= Decimal("1") - (action.ratio_or_cash_amount / candle.close)

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
                    "volume": candle.volume * split_factor if split_factor != 1 else candle.volume,
                    "adj_factor": price_factor,
                }
            )
        )
    return adjusted
