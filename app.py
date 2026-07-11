"""Fincent — personal research terminal. Streamlit entrypoint.

The front page is a technical dashboard: sentiment, RSI, and rule-based
enter/exit suggestions for one ticker. Deeper tools live in the sidebar
pages (Quote, Watchlist, Analytics, Agents).
"""

import streamlit as st

import ui
from analytics import technicals
from config import DASHBOARD_PERIODS, HISTORY_PERIODS, RSI_TIMEFRAMES
from data import DataSourceError, cache

st.set_page_config(page_title="Fincent", page_icon="📈", layout="wide")

st.title("📈 Fincent")
st.caption(
    "Quote — charts and ratios · Watchlist — saved tickers · "
    "Analytics — DCF and risk · Agents — 20 investor personas"
)
provider = ui.select_provider()

TECHNICALS_PERIOD = "1y"  # enough daily bars for the 200-day average

col_ticker, col_period, col_chart = st.columns([2, 1, 1])
ticker = col_ticker.text_input("Ticker", value="AAPL").strip().upper()
period = col_period.selectbox("Timeframe", DASHBOARD_PERIODS, index=2)
chart_type = col_chart.radio("Chart", ["Line", "Candles"], horizontal=True)
if not ticker:
    st.stop()

chart_range, chart_interval = HISTORY_PERIODS[period]
try:
    with st.spinner(f"Fetching {ticker}..."):
        snapshot = cache.get_snapshot(ticker, provider)
        chart_history = cache.get_history(
            ticker, chart_range, chart_interval, provider
        )
        history = cache.get_history(ticker, TECHNICALS_PERIOD, provider=provider)
except DataSourceError as exc:
    st.error(str(exc))
    st.stop()

ui.show_source_banner(snapshot["source"], provider)

quote = snapshot["quote"]
summary = technicals.build_summary(history["Close"])
verdict = technicals.sentiment(summary)

st.subheader(quote["name"])
ui.render_price_chart(ui.slice_intraday_window(chart_history, period), chart_type)

# --- What is the sentiment ---
_SENTIMENT_ICONS = {"Bullish": "🟢", "Neutral": "🟡", "Bearish": "🔴"}
sentiment_cols = st.columns(3)
sentiment_cols[0].metric(
    "Sentiment", f"{_SENTIMENT_ICONS[verdict['label']]} {verdict['label']}"
)
sentiment_cols[1].metric("Price", f"{quote['price']:,.2f} {quote['currency'] or ''}".strip())
sentiment_cols[2].metric(
    "1-month move",
    "N/A" if summary["return_1mo"] is None else f"{summary['return_1mo']:+.1%}",
)
with st.expander("Why this sentiment?"):
    for reason in verdict["reasons"]:
        st.markdown(f"- {reason}")
    st.caption(
        "Sentiment tallies simple votes: price vs. the 20/50/200-day "
        "averages, RSI momentum, and the 1-month return."
    )

# --- RSI information (computed on the selected timeframe's own bars) ---
st.header("RSI")
rsi_range, rsi_interval, rsi_resample, bar_label = RSI_TIMEFRAMES[period]
timeframe_rsi = None
try:
    rsi_history = cache.get_history(ticker, rsi_range, rsi_interval, provider)
    timeframe_prices = technicals.resample_closes(rsi_history["Close"], rsi_resample)
    timeframe_rsi = technicals.rsi(timeframe_prices)
except DataSourceError:
    st.caption(f"Could not fetch {bar_label} bars for this timeframe's RSI.")

daily_rsi = summary["rsi_14"]
rsi_cols = st.columns(3)
rsi_cols[0].metric(
    f"RSI — {bar_label} bars",
    "N/A" if timeframe_rsi is None else f"{timeframe_rsi:.0f}",
)
rsi_cols[1].metric("Zone", technicals.rsi_zone(timeframe_rsi).capitalize())
if bar_label != "daily":
    rsi_cols[2].metric(
        "RSI — daily (for comparison)",
        "N/A" if daily_rsi is None else f"{daily_rsi:.0f}",
    )
if timeframe_rsi is not None:
    st.progress(int(timeframe_rsi), text="0 — oversold · 100 — overbought")
st.markdown(technicals.rsi_signal(timeframe_rsi, bar_label))
st.caption(
    "RSI (Relative Strength Index) measures the speed of recent price "
    "changes on a 0-100 scale — above 70 is overbought, below 30 is "
    "oversold. It's computed over 14 bars of the chart's timeframe "
    f"(currently {bar_label} bars), which is how traders read 'the 4-hour "
    "RSI' vs 'the daily RSI': shorter bars flag short-lived swings, longer "
    "bars flag durable ones."
)

# --- Enter / Exit suggestions ---
enter_col, exit_col = st.columns(2)
with enter_col:
    st.header("Enter suggestions")
    for suggestion in technicals.enter_suggestions(summary):
        st.markdown(f"- {suggestion}")
with exit_col:
    st.header("Exit suggestions")
    for suggestion in technicals.exit_suggestions(summary):
        st.markdown(f"- {suggestion}")

st.divider()
st.caption(
    "Sentiment, RSI, and the enter/exit signals are computed on one year of "
    "daily bars regardless of the chart timeframe above. Signals are "
    "rule-based readings of standard indicators (RSI, moving averages) — "
    "informational only, not financial advice. Cross-check with the "
    "Analytics page (DCF, risk) and the Agents page before acting."
)
