"""Watchlist page: saved tickers with current prices, SQLite-backed."""

import streamlit as st

import ui
from data import cache, yahoo
from storage import db

ui.apply_theme()
st.title("Watchlist")
provider = ui.select_provider()

with st.form("add_ticker", clear_on_submit=True):
    col_input, col_button = st.columns([3, 1])
    new_symbol = col_input.text_input("Add ticker", placeholder="e.g. MSFT")
    submitted = col_button.form_submit_button("Add")
if submitted and new_symbol.strip():
    db.add_ticker(new_symbol)
    st.rerun()

symbols = db.list_tickers()
if not symbols:
    st.info("Watchlist is empty — add a ticker above.")
    st.stop()

with st.spinner("Fetching prices..."):
    snapshots = cache.get_snapshots(tuple(symbols), provider)

rows = []
any_fallback = False
for symbol in symbols:
    snapshot = snapshots.get(symbol)
    if snapshot is None:
        rows.append({"Ticker": symbol, "Name": "(no data)", "Price": "N/A"})
        continue
    is_fallback = snapshot["source"] == yahoo.SOURCE_FALLBACK
    any_fallback = any_fallback or is_fallback
    quote = snapshot["quote"]
    rows.append(
        {
            "Ticker": symbol,
            "Name": quote["name"] + (" ⚠" if is_fallback else ""),
            "Price": f"{quote['price']:,.2f}",
        }
    )

st.dataframe(rows, width='stretch', hide_index=True)
if any_fallback:
    st.caption("⚠ = Yahoo Finance unavailable; price is the last close from the fallback source.")

col_select, col_remove = st.columns([3, 1])
to_remove = col_select.selectbox("Remove ticker", symbols, label_visibility="collapsed")
if col_remove.button("Remove"):
    db.remove_ticker(to_remove)
    st.rerun()
