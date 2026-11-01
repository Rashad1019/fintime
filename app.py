"""Fincent. Type a ticker and learn what it is. Streamlit entrypoint.

One page for someone who just heard about a stock or fund: what it is, how it
has done, whether now looks like a good entry, and what investors would say.
"""

import streamlit as st

import persona_panel
import ui
from analytics import technicals
from config import DEFAULT_PERIOD, HISTORY_PERIODS, RISK_HISTORY_PERIOD
from data import DataSourceError, cache, yahoo
from formatting import escape_dollars, fmt_money, fmt_pct, fmt_ratio

st.set_page_config(page_title="Fincent", page_icon="📈", layout="wide")
ui.apply_theme()

ui.page_header(
    "Read the market.\nKnow the business.",
    "Fincent / independent market intelligence",
    "Price action, intrinsic value, risk, and sixteen investor frameworks — brought into one disciplined research view.",
    hero=True,
)
provider = ui.select_provider()

_MOOD_ICONS = {"Bullish": "🟢", "Neutral": "🟡", "Bearish": "🔴"}
_ENTRY_ICONS = {
    "Good entry": "🟢",
    "Possible entry": "🟡",
    "No clear signal": "🟡",
    "Wait": "🔴",
}


def _key_numbers(metrics: dict, profile: dict, is_fund: bool) -> list[tuple[str, str]]:
    """The few numbers worth showing a newcomer, skipping any we don't have."""
    if is_fund:
        rows = [
            ("Yearly fee", profile.get("expense_ratio"), fmt_pct),
            ("Dividend yield", metrics["dividend_yield"], fmt_pct),
            ("Yearly swing (volatility)", metrics["annualized_volatility"], fmt_pct),
            ("Bad-day loss (95%)", metrics["historical_var_95"], fmt_pct),
        ]
    else:
        rows = [
            ("Company value", metrics["market_cap"], fmt_money),
            ("P/E ratio", metrics["pe_ratio"], fmt_ratio),
            ("Dividend yield", metrics["dividend_yield"], fmt_pct),
            ("Profit margin", metrics["profit_margin"], fmt_pct),
            ("Yearly swing (volatility)", metrics["annualized_volatility"], fmt_pct),
            ("Bad-day loss (95%)", metrics["historical_var_95"], fmt_pct),
        ]
    return [(label, render(value)) for label, value, render in rows if value is not None]


ticker = ui.ticker_input("Enter a stock or fund ticker")
if not ticker:
    st.stop()

try:
    with st.spinner(f"Looking up {ticker}..."):
        snapshot = cache.get_snapshot(ticker, provider)
        risk_history = cache.get_history(ticker, RISK_HISTORY_PERIOD, provider=provider)
        profile = cache.get_profile(ticker)
except DataSourceError:
    st.error(f"We couldn't find {ticker}. Check the symbol and try again.")
    st.stop()

quote = snapshot["quote"]
fundamentals = yahoo.fundamentals_or_price(snapshot)
is_fund = bool(fundamentals.get("is_fund"))
ui.ticker_title(quote, ticker, profile, is_fund)

st.subheader("What it is")
about_slot = st.empty()

st.subheader("How it has done")
labels = list(HISTORY_PERIODS)
period = st.radio(
    "Timeframe",
    labels,
    index=labels.index(DEFAULT_PERIOD),
    horizontal=True,
    label_visibility="collapsed",
)
chart_range, chart_interval = HISTORY_PERIODS[period]
try:
    history = cache.get_history(ticker, chart_range, chart_interval, provider)
except DataSourceError:
    st.warning(f"No price chart for this timeframe. Showing {RISK_HISTORY_PERIOD} instead.")
    period = "1 year"
    history = risk_history
ui.move_sentence(technicals.period_return(history["Close"]), period)
candles = st.toggle("Show candlesticks")
ui.render_price_chart(history, "Candles" if candles else "Line")

st.subheader("Is now a good time?")
summary = technicals.build_summary(risk_history["Close"])
mood = technicals.sentiment(summary)
entry = technicals.entry_read(summary)
mood_col, entry_col = st.columns(2)
mood_col.metric("Trend right now", f"{_MOOD_ICONS[mood['label']]} {mood['label']}")
entry_col.metric("Entry point", f"{_ENTRY_ICONS[entry['label']]} {entry['label']}")
st.write(entry["why"])
with st.expander("How we got this"):
    for reason in mood["reasons"]:
        st.markdown(f"- {reason}")
    for suggestion in technicals.exit_suggestions(summary):
        st.markdown(f"- {suggestion}")
    st.caption(
        "Simple rules on a year of daily prices: moving averages, RSI "
        "momentum, and the one-month move. They read the chart, not the "
        "business, and they can be wrong."
    )
st.caption("Information only, not financial advice.")

metrics = persona_panel.metrics_for(ticker, fundamentals, risk_history["Close"], provider)
numbers = _key_numbers(metrics, profile, is_fund)
if numbers:
    st.subheader("Key numbers")
    for start in range(0, len(numbers), 2):
        for column, (label, value) in zip(st.columns(2), numbers[start:start + 2]):
            column.metric(label, value)

with about_slot.container():
    with st.spinner("Writing a plain explanation..."):
        about, written_by_ai = cache.get_explanation(ticker)
    st.write(escape_dollars(about))
    if written_by_ai:
        st.caption("Written by AI from public fund and company information.")

persona_panel.render(ticker, metrics, quote, is_fund, provider)
