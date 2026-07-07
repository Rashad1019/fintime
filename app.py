"""Fincent — personal research terminal. Streamlit entrypoint."""

import streamlit as st

st.set_page_config(page_title="Fincent", page_icon="📈", layout="wide")

st.title("📈 Fincent")
st.caption("Personal research terminal — quotes, ratios, DCF, risk, and investor-persona analysis.")

st.markdown(
    """
Use the sidebar to navigate:

- **Quote** — look up a ticker: price chart, key stats, valuation ratios
- **Watchlist** — save tickers and see their current prices at a glance
- **Analytics** — DCF intrinsic-value calculator and risk metrics
- **Agents** — run a ticker's numbers past 20 investor personas, from Buffett and Graham to Cathie Wood and Ian Dunlap

Data comes from Yahoo Finance (free, no key) with a direct chart-API fallback.
Persona analysis uses OpenRouter — set `OPENROUTER_API_KEY` in `.env`.
"""
)

st.info(
    "To use from your phone: run "
    "`uv run streamlit run app.py --server.address 0.0.0.0` "
    "and open `http://<this-pc's-local-ip>:8501` on the same WiFi."
)
