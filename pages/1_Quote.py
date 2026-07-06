"""Quote page: ticker lookup, price chart, key stats, valuation ratios."""

import streamlit as st

from analytics.ratios import compute_ratios
from data import DataSourceError, yfinance_source
from formatting import fmt_money, fmt_pct, fmt_ratio

st.title("Quote")

col_ticker, col_period = st.columns([2, 1])
ticker = col_ticker.text_input("Ticker", value="AAPL").strip().upper()
period = col_period.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)

if not ticker:
    st.stop()

try:
    with st.spinner(f"Fetching {ticker}..."):
        quote = yfinance_source.get_quote(ticker)
        history = yfinance_source.get_history(ticker, period)
except DataSourceError as exc:
    st.error(str(exc))
    st.stop()

st.subheader(quote["name"])
metric_cols = st.columns(3)
metric_cols[0].metric("Price", f"{quote['price']:,.2f} {quote['currency'] or ''}".strip())
metric_cols[1].metric("Market cap", fmt_money(quote["market_cap"]))
metric_cols[2].metric("Ticker", quote["ticker"])

st.line_chart(history["Close"])

st.subheader("Valuation ratios")
try:
    with st.spinner("Fetching fundamentals..."):
        fundamentals = yfinance_source.get_fundamentals(ticker)
    ratios = compute_ratios(fundamentals)
    ratio_cols = st.columns(5)
    ratio_cols[0].metric("P/E", fmt_ratio(ratios["pe_ratio"]))
    ratio_cols[1].metric("P/B", fmt_ratio(ratios["pb_ratio"]))
    ratio_cols[2].metric("ROE", fmt_pct(ratios["roe"]))
    ratio_cols[3].metric("Debt/Equity", fmt_ratio(ratios["debt_to_equity"]))
    ratio_cols[4].metric("Net margin", fmt_pct(ratios["profit_margin"]))

    with st.expander("Raw fundamentals"):
        st.table(
            {
                "EPS (TTM)": [fmt_ratio(fundamentals["eps"])],
                "Revenue": [fmt_money(fundamentals["revenue"])],
                "Net income": [fmt_money(fundamentals["net_income"])],
                "Free cash flow": [fmt_money(fundamentals["free_cash_flow"])],
                "Total debt": [fmt_money(fundamentals["total_debt"])],
            }
        )
except DataSourceError as exc:
    st.warning(f"Ratios unavailable: {exc}")
