"""Shared Streamlit UI helpers used across pages."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import INTRADAY_WINDOW_HOURS
from data import yahoo

_PROVIDER_LABELS = {
    yahoo.PROVIDER_AUTO: "Auto (Yahoo → FMP → Backup)",
    yahoo.SOURCE_YAHOO: "Yahoo Finance",
    yahoo.SOURCE_FMP: "Financial Modeling Prep (FMP)",
    yahoo.SOURCE_FALLBACK: "Backup (Yahoo chart API)",
}

_SOURCE_NAMES = {
    yahoo.SOURCE_YAHOO: "Yahoo Finance",
    yahoo.SOURCE_FMP: "FMP",
    yahoo.SOURCE_FALLBACK: "the backup chart API",
}


def select_provider() -> str:
    """Sidebar data-provider picker, shared across pages via session state."""
    return st.sidebar.selectbox(
        "Data provider",
        options=list(_PROVIDER_LABELS),
        format_func=_PROVIDER_LABELS.get,
        key="data_provider",
        help=(
            "Auto tries Yahoo first and degrades to FMP, then the raw chart "
            "API. Pick a specific provider to force it."
        ),
    )


def show_source_banner(source: str, provider: str) -> None:
    """Tell the user where the data came from when it isn't plain Yahoo."""
    if provider == yahoo.PROVIDER_AUTO:
        if source == yahoo.SOURCE_FMP:
            st.info("Yahoo Finance is unavailable — showing data from the FMP backup.")
        elif source == yahoo.SOURCE_FALLBACK:
            st.warning(
                "Yahoo Finance and the FMP backup are both unavailable — "
                "showing the last close from the Yahoo chart API. Name, "
                "market cap, and fundamentals are missing."
            )
        return
    name = _SOURCE_NAMES.get(source, source)
    st.caption(f"Data source: {name} (selected in the sidebar).")
    if source == yahoo.SOURCE_FALLBACK:
        st.warning(
            "The backup chart API only provides prices — name, market cap, "
            "and fundamentals are unavailable on this provider."
        )


def slice_intraday_window(history: pd.DataFrame, period: str) -> pd.DataFrame:
    """Trim a day's bars down to the last N hours for sub-day periods.

    Yahoo has no 1-hour or 4-hour range, so those periods fetch a full day
    of intraday bars and slice the tail here.
    """
    hours = INTRADAY_WINDOW_HOURS.get(period)
    if not hours:
        return history
    cutoff = history.index.max() - pd.Timedelta(hours=hours)
    return history[history.index >= cutoff]


def render_price_chart(history: pd.DataFrame, chart_type: str) -> None:
    """Candlestick chart when OHLC is available, line chart otherwise."""
    has_ohlc = {"Open", "High", "Low"}.issubset(history.columns)
    if chart_type == "Candles" and has_ohlc:
        fig = go.Figure(
            go.Candlestick(
                x=history.index,
                open=history["Open"],
                high=history["High"],
                low=history["Low"],
                close=history["Close"],
            )
        )
        fig.update_layout(
            xaxis_rangeslider_visible=False,
            margin=dict(l=0, r=0, t=10, b=0),
            height=420,
        )
        st.plotly_chart(fig, use_container_width=True)
        return
    if chart_type == "Candles" and not has_ohlc:
        st.caption("Candles unavailable for this data source — showing line chart.")
    st.line_chart(history["Close"])
