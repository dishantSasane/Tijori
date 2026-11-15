"""Sizing algorithm, exact per docs/specs/RISK_ENGINE_SPEC.md §3.

`floor` at every step, never `round` (invariant I9) — this module is what
actually prevents a rounded-up/negative/zero-submitted quantity from ever
being computed, not just a contract-level check after the fact.
"""

from __future__ import annotations

import math
from decimal import Decimal

from trading.core.models import BrainVerdict


def floor_to_lot_size(qty: Decimal, lot_size: Decimal) -> Decimal:
    if lot_size <= 0:
        raise ValueError("lot_size must be positive")
    lots = math.floor(qty / lot_size)
    return Decimal(lots) * lot_size


def compute_qty(
    *,
    sleeve_equity: Decimal,
    risk_per_trade_pct: Decimal,
    entry_ref: Decimal,
    stop: Decimal,
    max_position_value_pct: Decimal,
    lot_size: Decimal = Decimal(1),
    liquidity_cap_qty: Decimal | None = None,
    brain_verdict: BrainVerdict | None = None,
) -> Decimal:
    risk_distance = abs(entry_ref - stop)
    if risk_distance <= 0:
        raise ValueError("risk distance must be positive")

    risk_budget = sleeve_equity * risk_per_trade_pct / Decimal(100)
    raw_qty = Decimal(math.floor(risk_budget / risk_distance))

    position_value_cap = (max_position_value_pct * sleeve_equity / Decimal(100)) / entry_ref
    qty = min(raw_qty, Decimal(math.floor(position_value_cap)))

    if liquidity_cap_qty is not None:
        qty = min(qty, liquidity_cap_qty)

    qty = floor_to_lot_size(qty, lot_size)

    if brain_verdict is not None:
        qty = floor_to_lot_size(qty * brain_verdict.size_multiplier, lot_size)

    return max(qty, Decimal(0))
