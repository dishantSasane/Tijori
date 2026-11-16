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
    range. Split/bonus dates inside that range remain blocked because share
    count and cost-basis replay is not implemented.
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
    if any(
        notice.kind in {CorporateActionKind.SPLIT, CorporateActionKind.BONUS}
        and notice.symbol in symbols
        and start <= notice.effective_date <= end
        for notice in notices
    ):
        raise ValueError("share-action replay is not implemented; action-crossing window blocked")
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
