"""Shared Streamlit UI helpers used across pages.

Visual identity: "Midnight Blue" — a dark, modern fintech aesthetic.
Palette and fonts are defined once in THEME/apply_theme() so every page
stays visually consistent; call ui.apply_theme() right after
st.set_page_config() on every page.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import INTRADAY_WINDOW_HOURS
from data import yahoo

# Single source of truth for the palette — reused by CSS injection and by
# the Plotly chart colors so charts match the chrome around them.
THEME = {
    "background": "#0B1220",
    "surface": "#131D2E",
    "surface_alt": "#1A273B",
    "border": "#263852",
    "primary": "#3B82F6",
    "text": "#F1F5F9",
    "text_muted": "#94A3B8",
    "positive": "#22C55E",
    "negative": "#F87171",
    "font_body": "'Inter', sans-serif",
    "font_mono": "'JetBrains Mono', monospace",
}

_GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Inter:wght@400;500;600;700&"
    "family=JetBrains+Mono:wght@400;500;600&display=swap"
)


def apply_theme() -> None:
    """Inject fonts and CSS for the Midnight Blue look.

    Call once per page, right after st.set_page_config(). Idempotent —
    Streamlit re-renders this markdown block on every rerun harmlessly.
    """
    t = THEME
    st.markdown(
        f"""
        <style>
        @import url('{_GOOGLE_FONTS_URL}');

        html, body, [class*="css"] {{
            font-family: {t["font_body"]};
        }}

        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stHeader"] {{
            background-color: {t["background"]};
        }}

        [data-testid="stAppViewContainer"] {{
            color: {t["text"]};
        }}

        h1, h2, h3, h4 {{
            font-family: {t["font_body"]};
            font-weight: 600;
            letter-spacing: 0.01em;
        }}

        /* Numeric displays read as terminal data, not prose. */
        [data-testid="stMetricValue"] {{
            font-family: {t["font_mono"]};
            font-weight: 600;
        }}
        [data-testid="stMetricLabel"] {{
            font-family: {t["font_body"]};
            color: {t["text_muted"]};
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }}
        [data-testid="stMetricDelta"] {{
            font-family: {t["font_mono"]};
        }}
        [data-testid="stMetric"] {{
            background-color: {t["surface"]};
            border: 1px solid {t["border"]};
            border-radius: 2px;
            padding: 0.85rem 1rem;
        }}

        code, .stCode, [data-testid="stCode"] {{
            font-family: {t["font_mono"]} !important;
        }}

        [data-testid="stSidebar"] {{
            background-color: {t["surface"]};
            border-right: 1px solid {t["border"]};
        }}

        /* Hairline borders, no shadows — matches bordered containers,
           expanders, and dataframes to the terminal-panel language. */
        [data-testid="stVerticalBlockBorderWrapper"] > div,
        [data-testid="stExpander"],
        [data-testid="stDataFrame"] {{
            border: 1px solid {t["border"]} !important;
            border-radius: 2px !important;
            box-shadow: none !important;
        }}

        .stAlert {{
            border: 1px solid {t["border"]};
            border-radius: 2px;
            box-shadow: none;
        }}

        button[kind="primary"] {{
            background-color: {t["primary"]};
            color: {t["background"]};
            border-radius: 2px;
            border: none;
            font-weight: 600;
        }}
        button[kind="secondary"] {{
            border-radius: 2px;
            border: 1px solid {t["border"]};
        }}

        hr {{
            border-color: {t["border"]};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


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


def _themed_layout(fig: go.Figure) -> go.Figure:
    """Apply the terminal-dark chart chrome shared by both chart types."""
    t = THEME
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=10, b=0),
        height=420,
        paper_bgcolor=t["surface"],
        plot_bgcolor=t["surface"],
        font=dict(family=t["font_body"], color=t["text_muted"]),
        xaxis=dict(gridcolor=t["border"], showgrid=True, zeroline=False),
        yaxis=dict(gridcolor=t["border"], showgrid=True, zeroline=False),
    )
    return fig


def render_price_chart(history: pd.DataFrame, chart_type: str) -> None:
    """Candlestick chart when OHLC is available, line chart otherwise.

    Both use Plotly (not st.line_chart) so colors stay on-theme.
    """
    t = THEME
    has_ohlc = {"Open", "High", "Low"}.issubset(history.columns)
    if chart_type == "Candles" and has_ohlc:
        fig = go.Figure(
            go.Candlestick(
                x=history.index,
                open=history["Open"],
                high=history["High"],
                low=history["Low"],
                close=history["Close"],
                increasing_line_color=t["positive"],
                decreasing_line_color=t["negative"],
                increasing_fillcolor=t["positive"],
                decreasing_fillcolor=t["negative"],
            )
        )
        st.plotly_chart(_themed_layout(fig), width='stretch')
        return
    if chart_type == "Candles" and not has_ohlc:
        st.caption("Candles unavailable for this data source — showing line chart.")
    fig = go.Figure(
        go.Scatter(
            x=history.index,
            y=history["Close"],
            mode="lines",
            line=dict(color=t["primary"], width=1.75),
            fill="tozeroy",
            fillcolor="rgba(255, 176, 32, 0.08)",
        )
    )
    st.plotly_chart(_themed_layout(fig), width='stretch')
