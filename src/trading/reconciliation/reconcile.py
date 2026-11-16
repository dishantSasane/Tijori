"""Compare our recorded positions (SQLite `state_db.py`, via the broker's
`open_positions()`/`positions()`) against the broker's own reported positions.

Pure comparison lives in `reconcile()` — no side effects, easy to unit test.
The side-effecting part (`run_drill()`) is a thin adapter that writes an
audit event and engages the kill switch on any mismatch, per AGENTS.md §4.2
("fail closed ... stop opening new positions, alert the human, keep
protective stops. Never 'continue anyway'"). It never calls a broker and
never places an order — it only reads positions and may engage a kill
switch that *blocks* new entries.

Tested only against a fake `Broker`/position source that can be told to
disagree with local state (see `tests/reconciliation/`) — never a real
broker, per AGENTS.md §4.4.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from trading.risk.audit import AuditLog
from trading.risk.kill_switch import KillSwitch


@dataclass(frozen=True)
class BrokerPosition:
    """The broker's view of one open position. Deliberately a separate,
    minimal type from `OpenPosition`/`Position` — reconciliation must not
    assume the broker's shape matches ours; a mapping adapter per broker
    builds this from whatever that broker's API returns.
    """

    market: str
    symbol: str
    qty: Decimal


class LocalPosition(Protocol):
    """Shape `reconcile()` needs from our own recorded positions — satisfied
    by `OpenPosition` (paper broker) without importing it, so this module
    has no dependency on a specific broker implementation.
    """

    market: str
    symbol: str
    qty: Decimal


@dataclass(frozen=True)
class Mismatch:
    market: str
    symbol: str
    local_qty: Decimal | None  # None = broker has it, we don't
    broker_qty: Decimal | None  # None = we have it, broker doesn't
    reason: str = "quantity_mismatch"


@dataclass(frozen=True)
class ReconciliationReport:
    mismatches: tuple[Mismatch, ...]
    checked_ts: datetime

    @property
    def clean(self) -> bool:
        return len(self.mismatches) == 0


def reconcile(
    local_positions: list[LocalPosition],
    broker_positions: list[BrokerPosition],
    *,
    now: datetime,
) -> ReconciliationReport:
    """Any quantity difference, or a position present on only one side, is a
    mismatch. There is no tolerance band: a trading system's own ledger
    must match the broker's exactly, or something is wrong (duplicate fill,
    missed fill, manual intervention, a bug) and a human must look before
    any new entry is allowed.
    """
    local_by_key: dict[tuple[str, str], Decimal] = {}
    broker_by_key: dict[tuple[str, str], Decimal] = {}
    duplicate_local: set[tuple[str, str]] = set()
    duplicate_broker: set[tuple[str, str]] = set()
    for position in local_positions:
        key = (position.market, position.symbol)
        if key in local_by_key:
            duplicate_local.add(key)
        local_by_key[key] = position.qty
    for position in broker_positions:
        key = (position.market, position.symbol)
        if key in broker_by_key:
            duplicate_broker.add(key)
        broker_by_key[key] = position.qty

    mismatches: list[Mismatch] = []
    for key in sorted(set(local_by_key) | set(broker_by_key)):
        local_qty = local_by_key.get(key)
        broker_qty = broker_by_key.get(key)
        if key in duplicate_local:
            mismatches.append(
                Mismatch(*key, local_qty, broker_qty, reason="duplicate_local_position")
            )
            continue
        if key in duplicate_broker:
            mismatches.append(
                Mismatch(*key, local_qty, broker_qty, reason="duplicate_broker_position")
            )
            continue
        if local_qty != broker_qty:
            mismatches.append(
                Mismatch(market=key[0], symbol=key[1], local_qty=local_qty, broker_qty=broker_qty)
            )
    return ReconciliationReport(mismatches=tuple(mismatches), checked_ts=now)


def run_drill(
    local_positions: list[LocalPosition],
    broker_positions: list[BrokerPosition],
    *,
    audit: AuditLog,
    kill_switch: KillSwitch,
    now: datetime,
    scope: str = "global",
) -> ReconciliationReport:
    """Run `reconcile()`, log the result, and — on any mismatch — engage the
    kill switch so the risk engine (checked first, per RISK_ENGINE_SPEC.md
    §2 check 1) rejects every new signal until a human investigates and
    releases it. Existing protective stops are untouched; this only blocks
    new entries, matching AGENTS.md §4.2.
    """
    report = reconcile(local_positions, broker_positions, now=now)
    audit.write(
        ts_utc=now,
        event_type="reconciliation_drill",
        actor="system",
        payload={
            "clean": report.clean,
            "mismatch_count": len(report.mismatches),
            "mismatches": [
                {
                    "market": m.market,
                    "symbol": m.symbol,
                    "local_qty": str(m.local_qty) if m.local_qty is not None else None,
                    "broker_qty": str(m.broker_qty) if m.broker_qty is not None else None,
                }
                for m in report.mismatches
            ],
        },
    )
    if not report.clean:
        kill_switch.engage(scope, "reconciliation_mismatch", actor="system", now=now)
    return report
