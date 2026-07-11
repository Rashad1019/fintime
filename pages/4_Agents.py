"""Agents page: run a ticker's computed numbers past investor personas."""

import streamlit as st

import ui
from agents import openrouter_client
from agents.personas import PERSONAS, build_prompt
from analytics import technicals
from analytics.dcf import dcf_value
from analytics.ratios import compute_ratios
from analytics.risk import annualized_volatility, historical_var, sharpe_ratio
from config import (
    DCF_DISCOUNT,
    DCF_GROWTH,
    DCF_TERMINAL_GROWTH,
    DCF_YEARS,
    RISK_HISTORY_PERIOD,
)
from data import DataSourceError, cache

ui.apply_theme()
st.title("Investor agents")
st.caption(
    "Each persona gets the ticker's real computed numbers — ratios, DCF, risk, "
    "technicals — so the analysis is grounded in data, not invented figures."
)
provider = ui.select_provider()

col_ticker, col_persona = st.columns([1, 2])
ticker = col_ticker.text_input("Ticker", value="AAPL").strip().upper()
persona_names = list(PERSONAS.keys())
selected = col_persona.multiselect(
    "Personas", persona_names, default=persona_names[:1]
)

if not st.button("Run analysis", type="primary") or not ticker or not selected:
    st.stop()

try:
    with st.spinner(f"Computing metrics for {ticker}..."):
        snapshot = cache.get_snapshot(ticker, provider)
        history = cache.get_history(ticker, RISK_HISTORY_PERIOD, provider=provider)
except DataSourceError as exc:
    st.error(str(exc))
    st.stop()

ui.show_source_banner(snapshot["source"], provider)

fundamentals = snapshot["fundamentals"]
if fundamentals is None:
    st.error(
        f"No fundamentals available for '{ticker}' right now — the personas "
        "need real numbers to analyze."
    )
    st.stop()

metrics = {
    "price": fundamentals["price"],
    "market_cap": fundamentals["market_cap"],
    "eps": fundamentals["eps"],
    "dividend_yield": fundamentals["dividend_yield"],
    "payout_ratio": fundamentals["payout_ratio"],
    "revenue": fundamentals["revenue"],
    "net_income": fundamentals["net_income"],
    "free_cash_flow": fundamentals["free_cash_flow"],
    **compute_ratios(fundamentals),
}

fcf = fundamentals["free_cash_flow"]
shares = fundamentals["shares_outstanding"]
if fcf and shares:
    total_value = dcf_value(fcf, DCF_GROWTH, DCF_DISCOUNT, DCF_TERMINAL_GROWTH, DCF_YEARS)
    metrics["dcf_value_per_share"] = total_value / shares

try:
    prices = history["Close"]
    metrics["annualized_volatility"] = annualized_volatility(prices)
    metrics["sharpe_ratio"] = sharpe_ratio(prices)
    metrics["historical_var_95"] = historical_var(prices)
except ValueError:
    pass  # persona prompt will show N/A for missing risk metrics

summary = technicals.build_summary(history["Close"])
verdict = technicals.sentiment(summary)
metrics["rsi_14"] = summary["rsi_14"]
metrics["return_1mo"] = summary["return_1mo"]
metrics["technical_sentiment"] = f"{verdict['label']} (score {verdict['score']:+d})"

with st.expander("Numbers given to the personas", expanded=False):
    st.code(build_prompt(ticker, metrics))
if "dcf_value_per_share" in metrics:
    st.caption(
        f"DCF assumes {DCF_GROWTH:.0%} growth, {DCF_DISCOUNT:.0%} discount rate, "
        f"{DCF_TERMINAL_GROWTH:.1%} terminal growth over {DCF_YEARS} years."
    )

user_prompt = build_prompt(ticker, metrics)
for name in selected:
    st.subheader(name)
    try:
        with st.spinner(f"{name} is thinking..."):
            reply = openrouter_client.ask(PERSONAS[name], user_prompt)
        st.markdown(reply)
    except openrouter_client.OpenRouterError as exc:
        st.error(str(exc))
