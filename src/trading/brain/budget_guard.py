"""Hard budget guard for Brain/LLM calls (docs/BRAIN_AND_COSTS.md §5).

Fails closed: `allow()` returning `False` means the caller must not make the
LLM call at all (not "make it and discard the result" — that would still
spend money). Spend is read back from the shared `audit_log` table
(`trading.storage.state_db`), so there is no separate ledger to drift out of
sync with the audit trail AGENTS.md §6 already requires for every LLM call.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from trading.risk.audit import AuditLog

LLM_CALL_EVENT = "llm_call"


@dataclass(frozen=True)
class BudgetStatus:
    spent_today_inr: Decimal
    spent_month_inr: Decimal
    daily_cap_inr: Decimal
    monthly_cap_inr: Decimal

    @property
    def allowed(self) -> bool:
        return (
            self.spent_today_inr < self.daily_cap_inr
            and self.spent_month_inr < self.monthly_cap_inr
        )


class BudgetGuard:
    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        daily_cap_inr: Decimal,
        monthly_cap_inr: Decimal,
    ) -> None:
        self._conn = conn
        self._audit = AuditLog(conn)
        self.daily_cap_inr = daily_cap_inr
        self.monthly_cap_inr = monthly_cap_inr

    def _spent_since(self, since: datetime) -> Decimal:
        cur = self._conn.execute(
            "SELECT payload_json FROM audit_log WHERE event_type = ? AND ts_utc >= ?",
            (LLM_CALL_EVENT, since.isoformat()),
        )
        total = Decimal(0)
        for (payload_json,) in cur.fetchall():
            payload = json.loads(payload_json)
            total += Decimal(str(payload["cost_inr"]))
        return total

    def status(self, now: datetime) -> BudgetStatus:
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_month = start_of_day.replace(day=1)
        return BudgetStatus(
            spent_today_inr=self._spent_since(start_of_day),
            spent_month_inr=self._spent_since(start_of_month),
            daily_cap_inr=self.daily_cap_inr,
            monthly_cap_inr=self.monthly_cap_inr,
        )

    def allow(self, now: datetime) -> bool:
        """True iff a new call is still within both caps. Call this BEFORE
        spending any tokens -- it does not itself prevent a call, the caller
        must check it and refuse to call the provider when False.
        """
        return self.status(now).allowed

    def record_call(
        self,
        *,
        now: datetime,
        provider: str,
        model: str,
        purpose: str,
        tokens_in: int,
        tokens_out: int,
        cost_inr: Decimal,
        signal_id: str | None,
        ok: bool,
    ) -> None:
        """Log every attempted call -- success or failure -- with tokens and
        INR cost, per AGENTS.md §4.8. A failed call that still consumed
        tokens (e.g. the provider billed before returning an error) must
        still be passed here with its real cost; a call that never reached
        the provider (blocked by `allow()`) is never recorded here.
        """
        self._audit.write(
            ts_utc=now,
            event_type=LLM_CALL_EVENT,
            actor=f"brain:{provider}",
            payload={
                "provider": provider,
                "model": model,
                "purpose": purpose,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_inr": str(cost_inr),
                "signal_id": signal_id,
                "ok": ok,
            },
        )
