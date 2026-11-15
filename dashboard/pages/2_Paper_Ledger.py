"""Paper ledger page (docs/PAGES.md §1): paper trades, fills, and
rejected-signal outcomes. Read-only.
"""

from __future__ import annotations

import streamlit as st

from dashboard._data import get_connection

st.set_page_config(page_title="Tijori — Paper ledger", page_icon="📒")
st.title("Paper ledger")

try:
    conn = get_connection()
except FileNotFoundError as exc:
    st.error(str(exc))
    st.stop()

st.subheader("Fills")
fills = conn.execute(
    "SELECT id, order_id, qty, price, fees, ledger_source, ts_utc"
    " FROM fills ORDER BY ts_utc DESC LIMIT 200"
).fetchall()
st.table(fills) if fills else st.write("No fills yet.")

st.subheader("Signal outcomes (including rejected signals' 'would have')")
outcomes = conn.execute(
    "SELECT signal_id, result, pct_after_costs, bars_held, closed_ts"
    " FROM signal_outcomes ORDER BY closed_ts DESC LIMIT 200"
).fetchall()
st.table(outcomes) if outcomes else st.write("No outcomes recorded yet.")
