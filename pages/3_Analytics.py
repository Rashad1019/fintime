"""Analytics page: DCF intrinsic-value calculator and risk metrics."""

import streamlit as st

from analytics.dcf import dcf_value
from analytics.risk import annualized_volatility, historical_var, sharpe_ratio
from config import (
    DCF_DISCOUNT,
    DCF_GROWTH,
    DCF_TERMINAL_GROWTH,
    DCF_YEARS,
    RISK_HISTORY_PERIOD,
)
import ui
from data import DataSourceError, cache
from formatting import fmt_money, fmt_pct

ui.apply_theme()
ui.page_header(
    "Analytics",
    "Valuation lab / risk desk",
    "Pressure-test intrinsic value assumptions and measure recent market risk.",
)
provider = ui.select_provider()

ticker = st.text_input("Ticker", value="AAPL").strip().upper()
if not ticker:
    st.stop()

try:
    with st.spinner(f"Fetching {ticker}..."):
        snapshot = cache.get_snapshot(ticker, provider)
        history = cache.get_history(ticker, RISK_HISTORY_PERIOD, provider=provider)
except DataSourceError as exc:
    st.error(str(exc))
    st.stop()

ui.show_source_banner(snapshot["source"], provider)

fundamentals = snapshot["fundamentals"]
if fundamentals is None:
    st.error(f"No fundamentals available for '{ticker}' right now — DCF needs them.")
    st.stop()

st.header("DCF intrinsic value")
st.caption("Pre-filled with the company's trailing free cash flow — adjust the assumptions.")

default_fcf = fundamentals["free_cash_flow"] or 0.0
input_cols = st.columns(5)
fcf = input_cols[0].number_input("Free cash flow", value=float(default_fcf), format="%.0f")
growth = input_cols[1].number_input("Growth rate %", value=DCF_GROWTH * 100, step=0.5) / 100
discount = input_cols[2].number_input("Discount rate %", value=DCF_DISCOUNT * 100, step=0.5) / 100
terminal = (
    input_cols[3].number_input("Terminal growth %", value=DCF_TERMINAL_GROWTH * 100, step=0.5) / 100
)
years = int(input_cols[4].number_input("Years", value=DCF_YEARS, min_value=1, max_value=20))

try:
    total_value = dcf_value(fcf, growth, discount, terminal, years)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

shares = fundamentals["shares_outstanding"]
result_cols = st.columns(3)
result_cols[0].metric("Intrinsic value (total)", fmt_money(total_value))
if shares:
    per_share = total_value / shares
    price = fundamentals["price"]
    upside = (per_share - price) / price
    result_cols[1].metric("Per share", f"{per_share:,.2f}")
    result_cols[2].metric(
        "vs. current price", f"{price:,.2f}", delta=fmt_pct(upside)
    )
else:
    result_cols[1].metric("Per share", "N/A (shares unknown)")

st.header(f"Risk metrics ({RISK_HISTORY_PERIOD} daily prices)")
try:
    prices = history["Close"]
    risk_cols = st.columns(3)
    risk_cols[0].metric("Annualized volatility", fmt_pct(annualized_volatility(prices)))
    sharpe = sharpe_ratio(prices)
    risk_cols[1].metric("Sharpe ratio", "N/A" if sharpe is None else f"{sharpe:.2f}")
    risk_cols[2].metric("1-day VaR (95%)", fmt_pct(historical_var(prices)))
except ValueError as exc:
    st.warning(f"Risk metrics unavailable: {exc}")
