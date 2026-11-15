"""Read-only per-sleeve balance view for the Usage/Accounts dashboard page
(P5 scope; `docs/BUILD_ORDER.md`). Pure function over data already in the
paper broker's SQLite state -- no new ledger, no new table.

What this does NOT give you yet: realized profit/loss. `positions`/`fills`
(see `src/trading/storage/state_db.py`) don't record which side (buy/sell)
each fill was on an exit, so matching entry vs. exit fills into a signed P&L
series isn't reliable from what's stored today. Building that out is a
separate, bigger piece (a proper trade ledger) -- speculative to build now
when the only ask is "balances, read-only, v1" (YAGNI). This view instead
shows: starting sleeve capital, cost basis locked in open positions, and the
resulting "capital available to deploy" -- enough to answer "do I have room
left in this sleeve", which is what a balances page is for pre-trade.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SleeveBalance:
    sleeve: str
    starting_capital: Decimal
    open_position_count: int
    cost_basis_in_open_positions: Decimal

    @property
    def capital_available(self) -> Decimal:
        return self.starting_capital - self.cost_basis_in_open_positions


def sleeve_balances(
    conn: sqlite3.Connection, *, sleeve_capital: dict[str, Decimal]
) -> list[SleeveBalance]:
    """One row per configured sleeve, in the order given by `sleeve_capital`
    (= `allocation_pct * global.paper_capital_inr`, computed by the caller
    from `config/risk.yaml` -- not re-derived here, so this stays a pure
    read over whatever capital split the owner has configured).
    """
    rows = conn.execute("SELECT sleeve, qty, avg_price FROM positions").fetchall()
    balances: list[SleeveBalance] = []
    for sleeve, capital in sleeve_capital.items():
        sleeve_rows = [r for r in rows if r[0] == sleeve]
        cost_basis = sum(
            (Decimal(qty) * Decimal(avg_price) for _, qty, avg_price in sleeve_rows),
            start=Decimal(0),
        )
        balances.append(
            SleeveBalance(
                sleeve=sleeve,
                starting_capital=capital,
                open_position_count=len(sleeve_rows),
                cost_basis_in_open_positions=cost_basis,
            )
        )
    return balances
