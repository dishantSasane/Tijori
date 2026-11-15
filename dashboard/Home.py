"""Home page (docs/PAGES.md §1): whole picture in one glance.

Run with: `streamlit run dashboard/Home.py`
Needs no live broker credentials -- read-only over the SQLite state DB.
"""

from __future__ import annotations

import streamlit as st

from dashboard._data import get_connection
from trading.reporting.daily_report import build_daily_report

st.set_page_config(page_title="Tijori — Home", page_icon="🏠")
st.title("Tijori — Home")

try:
    conn = get_connection()
except FileNotFoundError as exc:
    st.error(str(exc))
    st.stop()

mode_rows = conn.execute("SELECT scope, mode FROM mode_state").fetchall()
kill_rows = conn.execute(
    "SELECT scope, engaged, reason FROM kill_switch_state WHERE engaged = 1"
).fetchall()

col1, col2 = st.columns(2)
with col1:
    st.subheader("Mode per sleeve")
    if mode_rows:
        for scope, mode in mode_rows:
            st.write(f"**{scope}**: {mode}")
    else:
        st.write("No mode recorded yet.")
with col2:
    st.subheader("Kill switch")
    if kill_rows:
        for scope, _engaged, reason in kill_rows:
            st.error(f"ENGAGED — {scope}: {reason or 'no reason given'}")
    else:
        st.success("No kill switch engaged.")

st.subheader("Today's report")
today = st.date_input("Date (UTC)")
report = build_daily_report(conn, today.isoformat())
st.metric("Fills", report.fills)
st.metric("Signals rejected", report.signals_rejected)
st.metric("Realized P&L", str(report.realized_pnl))
st.markdown(report.to_markdown())
