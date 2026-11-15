"""Adjust verified raw daily and intraday candles for splits and bonuses.

The caller must establish the provider's adjustment basis. Upstox data already
reflects the observed NESTLEIND split, so that event must bypass this transform.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import Field, model_validator

from trading.core.enums import MarketId
from trading.core.models import Candle, Contract

INDIA_TIMEZONE = ZoneInfo("Asia/Kolkata")


class CorporateActionKind(StrEnum):
    SPLIT = "split"
    BONUS = "bonus"
    DEMERGER = "demerger"
    RIGHTS = "rights"
    DIVIDEND = "dividend"
    OTHER = "other"


class CorporateActionNotice(Contract):
    """Normalized NSE action row; it carries no inferred adjustment factor."""

    symbol: str = Field(min_length=1)
    kind: CorporateActionKind
    purpose: str = Field(min_length=1)
    effective_date: date
    source_ref: str = Field(min_length=1)


class UnhandledCorporateAction(Contract):
    """A dated action in the test window that is not proven adjusted."""

    symbol: str
    kind: CorporateActionKind
    effective_date: date
    purpose: str
    source_ref: str
    requires_review: bool = True
    reason: str = "unhandled corporate action; no automatic adjustment is applied"


class BacktestActionScreening(Contract):
    """Universe screen output; blocked symbols need event-level review."""

    eligible_symbols: tuple[str, ...]
    blocked_symbols: tuple[str, ...]
    flags: tuple[UnhandledCorporateAction, ...]


def _row_value(row: dict[str, object], *names: str) -> object | None:
    normalized = {
        str(key).strip().casefold().replace("_", "-"): value for key, value in row.items()
    }
    for name in names:
        value = normalized.get(name.casefold().replace("_", "-"))
        if value is not None and str(value).strip():
            return value
    return None


def _nse_date(value: object) -> date:
    text = str(value).strip()
    for pattern in ("%d-%b-%Y", "%d-%B-%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    raise ValueError(f"unsupported NSE corporate-action date: {text}")


def classify_corporate_action(purpose: str) -> CorporateActionKind:
    """Classify common NSE purpose text without interpreting action ratios."""
    normalized = " ".join(purpose.casefold().replace("-", " ").split())
    if "demerger" in normalized or "de merger" in normalized:
        return CorporateActionKind.DEMERGER
    if "right" in normalized:
        return CorporateActionKind.RIGHTS
    if "bonus" in normalized:
        return CorporateActionKind.BONUS
    if "split" in normalized or "sub division" in normalized or "subdivision" in normalized:
        return CorporateActionKind.SPLIT
    if "dividend" in normalized:
        return CorporateActionKind.DIVIDEND
    return CorporateActionKind.OTHER


def parse_nse_corporate_action_row(
    row: dict[str, object], *, source_ref: str
) -> CorporateActionNotice:
    """Normalize the relevant fields from a downloaded NSE corporate-action row."""
    symbol = _row_value(row, "symbol", "scrip code")
    purpose = _row_value(row, "purpose", "corporate action")
    effective_date = _row_value(row, "ex-date", "ex date", "effective date")
    if symbol is None or purpose is None or effective_date is None:
        raise ValueError("NSE action row requires symbol, purpose, and ex-date")
    purpose_text = str(purpose).strip()
    return CorporateActionNotice(
        symbol=str(symbol).strip().upper(),
        kind=classify_corporate_action(purpose_text),
        purpose=purpose_text,
        effective_date=_nse_date(effective_date),
        source_ref=source_ref,
    )


def inspect_unhandled_actions(
    notices: Iterable[CorporateActionNotice],
    *,
    symbols: set[str] | frozenset[str],
    start: date,
    end: date,
    handled_action_keys: set[tuple[str, date]] | frozenset[tuple[str, date]] = frozenset(),
) -> list[UnhandledCorporateAction]:
    """Flag in-window actions absent from the verified adjusted-action ledger.

    A split/bonus is considered handled only when its `(symbol, ex_date)` is
    explicitly present in ``handled_action_keys`` because either the input
    price history already includes the adjustment or the approved transform
    was applied. Demergers, rights issues,
    dividends, and unknown action descriptions remain review flags; no factor
    is inferred or applied.
    """
    if end < start:
        raise ValueError("backtest end must be on or after start")
    target_symbols = {symbol.strip().upper() for symbol in symbols}
    flags: list[UnhandledCorporateAction] = []
    for notice in notices:
        key = (notice.symbol, notice.effective_date)
        if notice.symbol not in target_symbols or not start <= notice.effective_date <= end:
            continue
        supported_action = notice.kind in {
            CorporateActionKind.SPLIT,
            CorporateActionKind.BONUS,
        }
        if supported_action and key in handled_action_keys:
            continue
        flags.append(
            UnhandledCorporateAction(
                symbol=notice.symbol,
                kind=notice.kind,
                effective_date=notice.effective_date,
                purpose=notice.purpose,
                source_ref=notice.source_ref,
            )
        )
    return sorted(flags, key=lambda item: (item.symbol, item.effective_date, item.kind.value))


def screen_backtest_symbols(
    notices: Iterable[CorporateActionNotice],
    *,
    symbols: set[str] | frozenset[str],
    start: date,
    end: date,
    handled_action_keys: set[tuple[str, date]] | frozenset[tuple[str, date]] = frozenset(),
    reviewed_action_keys: set[tuple[str, date, CorporateActionKind]]
    | frozenset[tuple[str, date, CorporateActionKind]] = frozenset(),
) -> BacktestActionScreening:
    """Exclude symbols with an unadjusted event unless that exact event was reviewed."""
    normalized_symbols = {symbol.strip().upper() for symbol in symbols}
    flags = inspect_unhandled_actions(
        notices,
        symbols=normalized_symbols,
        start=start,
        end=end,
        handled_action_keys=handled_action_keys,
    )
    blocked = {
        flag.symbol
        for flag in flags
        if (flag.symbol, flag.effective_date, flag.kind) not in reviewed_action_keys
    }
    return BacktestActionScreening(
        eligible_symbols=tuple(sorted(normalized_symbols - blocked)),
        blocked_symbols=tuple(sorted(blocked)),
        flags=tuple(flags),
    )


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
    cumulative price multiplier in ``adj_factor``. Input must be verified raw
    candles; already-adjusted input fails closed. Daily and intraday bars are
    assigned to a session using India local time, so bars on an ex-date are
    never adjusted, including the first intraday bar of that session.
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


def prepare_candles_for_storage(
    candles: Iterable[Candle],
    actions: Iterable[ShareAdjustment],
    *,
    as_of: date,
    provider_adjusted_action_keys: set[tuple[str, date]]
    | frozenset[tuple[str, date]] = frozenset(),
) -> list[Candle]:
    """Adjust verified raw candles before storage, omitting provider-adjusted events.

    ``provider_adjusted_action_keys`` must contain exact `(symbol, ex_date)`
    keys proven to already be reflected in the fetched series. The caller must
    still run ``inspect_unhandled_actions`` on the full action feed; this helper
    intentionally does not treat missing actions as proof of a clean window.
    """
    skipped = {
        (symbol.strip().upper(), effective_date)
        for symbol, effective_date in provider_adjusted_action_keys
    }
    applicable = [
        action
        for action in actions
        if (action.symbol.upper(), action.effective_date) not in skipped
    ]
    return adjust_for_share_actions(candles, applicable, as_of=as_of)
