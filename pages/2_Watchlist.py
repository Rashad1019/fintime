"""Watchlist page: saved tickers with current prices, SQLite-backed."""

import streamlit as st

from data import DataSourceError, yfinance_source
from storage import db

st.title("Watchlist")

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

rows = []
with st.spinner("Fetching prices..."):
    for symbol in symbols:
        try:
            quote = yfinance_source.get_quote(symbol)
            rows.append(
                {
                    "Ticker": symbol,
                    "Name": quote["name"],
                    "Price": f"{quote['price']:,.2f}",
                }
            )
        except DataSourceError:
            rows.append({"Ticker": symbol, "Name": "(no data)", "Price": "N/A"})

st.dataframe(rows, use_container_width=True, hide_index=True)

col_select, col_remove = st.columns([3, 1])
to_remove = col_select.selectbox("Remove ticker", symbols, label_visibility="collapsed")
if col_remove.button("Remove"):
    db.remove_ticker(to_remove)
    st.rerun()
