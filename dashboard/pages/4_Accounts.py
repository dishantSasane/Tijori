"""Usage/Accounts page v1 (P5): read-only per-sleeve balances.

NOTE on duplication: `dashboard/` does not exist on `main` yet. PR #56 (P3)
and PR #57 (P4) each add a `dashboard/` tree with their own Home/pages
structure, both still open/unmerged. This page is written standalone so it
doesn't depend on either unmerged PR's layout; whichever of #56/#57/#58
(this one) merges first should absorb the others' pages into one `dashboard/`
app rather than keeping three parallel copies -- same situation flagged in
P4's handoff note 0037. State the merge order in the PR description.

Run: `streamlit run dashboard/pages/4_Accounts.py` (needs `pip install -e
.[dashboard]`). Points at `config/risk.yaml` (or its `.example.yaml`) and
whichever paper-broker SQLite file `TRADING_STATE_DB` points at.
"""

from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path

import streamlit as st

from trading.core.config import load_yaml
from trading.reporting.accounts import sleeve_balances
from trading.storage.state_db import connect

REPO_ROOT = Path(__file__).resolve().parents[2]


def _sleeve_capital() -> dict[str, Decimal]:
    risk = load_yaml(REPO_ROOT / "config" / "risk.yaml")
    total = Decimal(str(risk["global"]["paper_capital_inr"]))
    sleeves = risk.get("sleeves", {})
    return {
        name: (total * Decimal(str(block["allocation_pct"])) / Decimal(100))
        for name, block in sleeves.items()
        if block.get("enabled")
    }


def main() -> None:
    st.title("Accounts (paper, read-only)")
    st.caption(
        "Starting capital per enabled sleeve, cost basis locked in open paper "
        "positions, and capital still available to deploy. This is NOT a P&L "
        "statement -- realized profit/loss needs a trade ledger this repo "
        "doesn't have yet (see `src/trading/reporting/accounts.py` docstring)."
    )

    db_path = os.environ.get("TRADING_STATE_DB", str(REPO_ROOT / "state.db"))
    conn = connect(db_path)
    try:
        capital = _sleeve_capital()
        if not capital:
            st.warning("No enabled sleeves in config/risk.yaml.")
            return
        balances = sleeve_balances(conn, sleeve_capital=capital)
        st.table(
            [
                {
                    "sleeve": b.sleeve,
                    "starting_capital": f"{b.starting_capital:,.2f}",
                    "open_positions": b.open_position_count,
                    "cost_basis_locked": f"{b.cost_basis_in_open_positions:,.2f}",
                    "capital_available": f"{b.capital_available:,.2f}",
                }
                for b in balances
            ]
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
