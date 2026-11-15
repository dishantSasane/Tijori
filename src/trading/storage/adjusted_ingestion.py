"""Corporate-action-safe append path shared by daily and intraday loaders."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date
from hashlib import sha256

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
    candle_list = list(candles)
    action_list = tuple(actions)
    prepared = prepare_candles_for_storage(
        candle_list,
        action_list,
        as_of=as_of,
        provider_adjusted_action_keys=provider_adjusted_action_keys,
    )
    skipped_keys = sorted(
        (symbol.strip().upper(), effective_date.isoformat())
        for symbol, effective_date in provider_adjusted_action_keys
    )
    ledger_payload = [
        action.model_dump(mode="json")
        for action in sorted(
            action_list,
            key=lambda item: (item.event_id, item.revision, item.action_id),
        )
    ]
    ledger_hash = sha256(
        json.dumps(ledger_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    basis_hash = sha256(
        json.dumps(
            {
                "as_of": as_of.isoformat(),
                "ledger_hash": ledger_hash,
                "provider_adjusted_action_keys": skipped_keys,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    bases = {
        (candle.market, candle.symbol, candle.timeframe): (as_of, ledger_hash, basis_hash)
        for candle in prepared
    }
    return store.append_with_adjustment_bases(prepared, bases)
