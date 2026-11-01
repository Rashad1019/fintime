"""Agents page: run a ticker's computed numbers past investor personas."""

import streamlit as st

import persona_panel
import ui
from config import RISK_HISTORY_PERIOD
from data import DataSourceError, cache, yahoo

ui.apply_theme()
ui.page_header(
    "Investor agents",
    "Framework studio / 16 perspectives",
    "Run real computed ratios, DCF, risk, and technicals through distinct investor frameworks.",
)
provider = ui.select_provider()

ticker = ui.ticker_input()
if not ticker:
    persona_panel.show_profiles(expanded=True)
    st.stop()

try:
    with st.spinner(f"Computing metrics for {ticker}..."):
        snapshot = cache.get_snapshot(ticker, provider)
        history = cache.get_history(ticker, RISK_HISTORY_PERIOD, provider=provider)
except DataSourceError as exc:
    st.error(str(exc))
    st.stop()

ui.show_source_banner(snapshot["source"], provider)
fundamentals = yahoo.fundamentals_or_price(snapshot)
if snapshot["fundamentals"] is None:
    st.info(
        "Company figures are missing. The personas will use the last price, "
        "payouts, and the risk and technical numbers from the price history. "
        "Earnings, cash flow, and the DCF stay blank."
    )
persona_panel.render(
    ticker,
    persona_panel.metrics_for(ticker, fundamentals, history["Close"], provider),
    snapshot["quote"],
    bool(fundamentals.get("is_fund")),
    provider,
)
