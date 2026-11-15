"""Stocks page (P4, docs/BUILD_ORDER.md): scanner ideas, read-only.

Shows the current shortlist with target/"reconsider" levels, plus whether
each idea already has an open paper position -- so the owner can tell "new
idea" apart from "already tracking this one."

Run with: `streamlit run dashboard/Home.py` (Streamlit picks up pages/ automatically).
"""

from __future__ import annotations

import json

import streamlit as st

from dashboard._data import get_connection
from trading.scanner.shortlist_store import active_shortlist

st.set_page_config(page_title="Tijori — Stocks", page_icon="🔎")
st.title("Tijori — Stocks (scanner shortlist)")
st.caption(
    "Ideas the daily scanner currently likes. 'Target' and 'Reconsider' are "
    "rough research levels, not orders -- nothing here trades automatically."
)

try:
    conn = get_connection()
except FileNotFoundError as exc:
    st.error(str(exc))
    st.stop()

shortlist = active_shortlist(conn)
if not shortlist:
    st.info("No active shortlist yet. Run the scanner to populate one.")
    st.stop()

open_positions = {
    (row[0], row[1]) for row in conn.execute("SELECT symbol, market FROM positions").fetchall()
}

for row in shortlist:
    symbol, market = row["symbol"], row["market"]
    has_paper_position = (symbol, market) in open_positions
    cols = st.columns([2, 2, 2, 2, 1])
    cols[0].markdown(f"**{symbol}** ({market})")
    cols[1].write(f"Target: {row['target_price']}")
    cols[2].write(f"Reconsider: {row['reconsider_price']}")
    cols[3].write(", ".join(json.loads(row["reasons_json"])))
    cols[4].write("📈 Paper" if has_paper_position else "—")
