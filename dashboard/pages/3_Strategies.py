"""Strategies page (docs/PAGES.md §1): registry and promotion history.
Read-only.
"""

from __future__ import annotations

import streamlit as st

from dashboard._data import get_connection

st.set_page_config(page_title="Tijori — Strategies", page_icon="📈")
st.title("Strategies")

try:
    conn = get_connection()
except FileNotFoundError as exc:
    st.error(str(exc))
    st.stop()

st.subheader("Promotion history")
promotions = conn.execute(
    "SELECT strategy_id, promoted, promoted_by, promoted_ts"
    " FROM strategy_promotions ORDER BY promoted_ts DESC"
).fetchall()
if promotions:
    st.table(promotions)
else:
    st.write(
        "No strategies promoted yet. Strategy instances live in "
        "`src/trading/strategies/` once T1/T2/T4/T6/ORB land on `main` (see "
        "docs/BUILD_ORDER.md P1b — not merged as of this page's writing)."
    )
