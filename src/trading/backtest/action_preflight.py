"""Shared India-equity action screening, independent of fill/accounting logic."""

from trading.core.models import Candle
from trading.storage.action_register import ActionRegister
from trading.storage.corporate_actions import (
    INDIA_TIMEZONE,
    CorporateActionKind,
    CorporateActionNotice,
    UnhandledCorporateAction,
    screen_backtest_symbols,
)

type ReviewedActionKey = str


def action_preflight(
    candles: list[Candle],
    *,
    action_register: ActionRegister | None,
    candle_snapshot_sha256: str | None,
    reviewed_action_keys: set[ReviewedActionKey] | frozenset[ReviewedActionKey],
) -> tuple[UnhandledCorporateAction, ...]:
    """Use one reviewed register as source of truth and fail closed by default.

    Unit-test candles explicitly tagged ``test`` may omit the register. Real
    candle inputs must be covered for every symbol across the complete replay
    range. A split/bonus notice inside that range still blocks replay for a
    symbol UNLESS **both**: (1) the register has a reviewed record tied to
    that *specific* notice -- matched on symbol, effective/ex-date, and
    kind, via `action_register.provider_adjusted_events`/
    `approved_adjustments` -- confirming a human reviewed exactly this
    event (not some other split/bonus on the same symbol, or a guess), and
    (2) every one of that symbol's candles in the window carries a non-null
    `adj_factor`, confirming the transform was actually run against this
    exact candle snapshot. `Candle.adj_factor` alone is never sufficient:
    it is an arbitrary numeric field (could be an identity `1`, or describe
    an unrelated transform) and proves nothing about which action it
    corresponds to on its own -- it is corroborating evidence for an
    already-reviewed event, not proof by itself. Share-count/cost-basis
    replay at the position level inside this runner is still not
    implemented; what this allows is replaying a window whose price
    *series* is already internally consistent across a specifically
    reviewed event, same bypass category as the existing NESTLEIND
    provider-adjusted case.
    """
    if not candles:
        return ()
    if action_register is None:
        if all(candle.source == "test" for candle in candles):
            return ()
        raise ValueError("reviewed corporate-action register is required before replay")
    if candle_snapshot_sha256 is None:
        raise ValueError("candle snapshot SHA-256 is required before replay")
    dates = [candle.ts_open_utc.astimezone(INDIA_TIMEZONE).date() for candle in candles]
    start, end = min(dates), max(dates)
    symbol_timeframes = {(candle.symbol, candle.timeframe) for candle in candles}
    uncovered = sorted(
        f"{symbol}/{timeframe.value}"
        for symbol, timeframe in symbol_timeframes
        if not action_register.covers(symbol, timeframe, start, end, candle_snapshot_sha256)
    )
    if uncovered:
        raise ValueError(
            "corporate-action register does not cover the replay window for: "
            + ", ".join(uncovered)
        )
    symbols = {symbol for symbol, _ in symbol_timeframes}
    notices: list[CorporateActionNotice] = list(action_register.notices())
    symbols_with_unadjusted_candles = {
        candle.symbol for candle in candles if candle.adj_factor is None
    }
    # A specific reviewed record keyed on (symbol, effective_date, kind) --
    # not just "this symbol has some reviewed event somewhere" -- for every
    # provider-adjusted or approved-raw action the register actually vouches
    # for as of this window's end.
    reviewed_share_action_keys = {
        (event.symbol, event.ex_date, event.action_type)
        for event in action_register.provider_adjusted_events(as_of=end)
    } | {
        (
            adjustment.symbol,
            adjustment.effective_date,
            CorporateActionKind.SPLIT if adjustment.kind == "split" else CorporateActionKind.BONUS,
        )
        for adjustment in action_register.approved_adjustments(as_of=end)
    }
    share_action_notices = [
        notice
        for notice in notices
        if notice.kind in {CorporateActionKind.SPLIT, CorporateActionKind.BONUS}
        and notice.symbol in symbols
        and start <= notice.effective_date <= end
    ]
    blocking_share_action_symbols = {
        notice.symbol
        for notice in share_action_notices
        if notice.symbol in symbols_with_unadjusted_candles
        or (notice.symbol, notice.effective_date, notice.kind) not in reviewed_share_action_keys
    }
    if blocking_share_action_symbols:
        raise ValueError(
            "share-action replay is not implemented; action-crossing window blocked for: "
            + ", ".join(sorted(blocking_share_action_symbols))
        )
    screen = screen_backtest_symbols(
        notices,
        symbols=symbols,
        start=start,
        end=end,
        reviewed_action_keys=reviewed_action_keys,
    )
    if screen.blocked_symbols:
        raise ValueError(
            "unhandled corporate actions block replay for: " + ", ".join(screen.blocked_symbols)
        )
    return screen.flags
