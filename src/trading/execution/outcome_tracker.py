"""OutcomeTracker: records signal -> order -> fill -> exit lifecycle.

docs/specs/PAPER_BROKER_SPEC.md §5. A rejected/shadow signal is scored the
same cost-honest way as a real one — never a free "you should have taken
this" claim (AGENTS.md teaching mandate: say what the trade-off is).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from trading.core.enums import OutcomeResult
from trading.core.models import SignalOutcome
from trading.storage.state_store import StateStore


class OutcomeTracker:
    def __init__(self, store: StateStore) -> None:
        self._store = store

    def record(
        self,
        signal_id: str,
        result: OutcomeResult,
        *,
        pct_after_costs: Decimal | None = None,
        bars_held: int | None = None,
        closed_ts: datetime | None = None,
    ) -> SignalOutcome:
        self._store.record_outcome(signal_id, result.value, pct_after_costs, bars_held, closed_ts)
        return SignalOutcome(
            signal_id=signal_id,
            result=result,
            pct_after_costs=pct_after_costs,
            bars_held=bars_held,
            closed_ts=closed_ts,
        )

    def get(self, signal_id: str) -> SignalOutcome | None:
        row = self._store.get_outcome(signal_id)
        if row is None:
            return None
        return SignalOutcome(
            signal_id=row["signal_id"],
            result=OutcomeResult(row["result"]),
            pct_after_costs=Decimal(row["pct_after_costs"]) if row["pct_after_costs"] else None,
            bars_held=row["bars_held"],
            closed_ts=datetime.fromisoformat(row["closed_ts"]) if row["closed_ts"] else None,
        )
