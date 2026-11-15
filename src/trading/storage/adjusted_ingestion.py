"""Corporate-action-safe append path shared by daily and intraday loaders."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from trading.core.models import Candle
from trading.storage.candles import CandleStore
from trading.storage.corporate_actions import ShareAdjustment, prepare_candles_for_storage


def append_adjusted_candles(
    store: CandleStore,
    candles: Iterable[Candle],
    actions: Iterable[ShareAdjustment],
    *,
    as_of: date,
    action_ledger_complete: bool,
    provider_adjusted_action_keys: set[tuple[str, date]]
    | frozenset[tuple[str, date]] = frozenset(),
) -> int:
    """Adjust candles before append, refusing an incomplete/unapproved ledger."""
    if not action_ledger_complete:
        raise ValueError("a complete, authorized corporate-action ledger is required")
    prepared = prepare_candles_for_storage(
        candles,
        actions,
        as_of=as_of,
        provider_adjusted_action_keys=provider_adjusted_action_keys,
    )
    return store.append(prepared)
