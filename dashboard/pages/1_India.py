"""India market page (docs/PAGES.md §1): open positions and pending signals
for the india market. Read-only.
"""

from __future__ import annotations

import streamlit as st

from dashboard._data import get_connection

st.set_page_config(page_title="Tijori — India", page_icon="🇮🇳")
st.title("India")

try:
    conn = get_connection()
except FileNotFoundError as exc:
    st.error(str(exc))
    st.stop()

st.subheader("Open positions")
positions = conn.execute(
    "SELECT symbol, sleeve, qty, avg_price, stop_price, target_price, opened_ts"
    " FROM positions WHERE market = 'india'"
).fetchall()
if positions:
    st.table(positions)
else:
    st.write("No open India positions.")

st.subheader("Pending signals (awaiting approval)")
pending = conn.execute(
    "SELECT signal_id, state, batch_id FROM telegram_decisions WHERE state = 'pending'"
).fetchall()
if pending:
    st.table(pending)
else:
    st.write("No signals pending approval.")
