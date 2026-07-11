"""Shared Streamlit UI helpers used across pages.

Visual identity: "Obsidian Signal" — a focused institutional terminal.
Palette and fonts are defined once in THEME/apply_theme() so every page
stays visually consistent; call ui.apply_theme() right after
st.set_page_config() on every page.
"""

from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import INTRADAY_WINDOW_HOURS
from data import yahoo

# Single source of truth for the palette — reused by CSS injection and by
# the Plotly chart colors so charts match the chrome around them.
THEME = {
    "background": "#070B12",
    "surface": "#0D1420",
    "surface_alt": "#121C2A",
    "border": "#213148",
    "primary": "#58E1C1",
    "secondary": "#8BA9FF",
    "text": "#F5F7FA",
    "text_muted": "#8E9AAF",
    "positive": "#40D898",
    "negative": "#FF6B7A",
    "font_body": "'Inter', sans-serif",
    "font_mono": "'JetBrains Mono', monospace",
}

_GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Inter:wght@400;500;600;700&"
    "family=JetBrains+Mono:wght@400;500;600&display=swap"
)


def apply_theme() -> None:
    """Inject fonts and CSS for the Obsidian Signal look.

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
        [data-testid="stAppViewContainer"] {{
            background:
                radial-gradient(circle at 88% 0%, rgba(88, 225, 193, 0.08), transparent 28rem),
                radial-gradient(circle at 25% 35%, rgba(139, 169, 255, 0.035), transparent 30rem),
                {t["background"]};
        }}

        [data-testid="stHeader"] {{
            background: rgba(7, 11, 18, 0.82);
            backdrop-filter: blur(16px);
            border-bottom: 1px solid rgba(33, 49, 72, 0.55);
        }}

        [data-testid="stAppViewContainer"] {{
            color: {t["text"]};
        }}

        .block-container {{
            max-width: 1320px;
            padding-top: 2.25rem;
            padding-bottom: 4rem;
        }}

        h1, h2, h3, h4 {{
            font-family: {t["font_body"]};
            font-weight: 600;
            letter-spacing: -0.025em;
            color: {t["text"]};
        }}

        h2 {{
            font-size: 1.35rem;
            margin-top: 1.5rem;
        }}

        p, label, [data-testid="stCaptionContainer"] {{
            color: {t["text_muted"]};
        }}

        /* Branded page masthead shared across the full app. */
        .fincent-page-header {{
            display: flex;
            align-items: center;
            gap: 1rem;
            min-height: 104px;
            margin: 0 0 1.35rem 0;
            padding: 1.25rem 1.4rem;
            background: linear-gradient(115deg, rgba(18, 28, 42, 0.96), rgba(13, 20, 32, 0.86));
            border: 1px solid {t["border"]};
            border-radius: 18px;
            box-shadow: 0 20px 55px rgba(0, 0, 0, 0.22);
            position: relative;
            overflow: hidden;
        }}

        .fincent-page-header::after {{
            content: "";
            position: absolute;
            width: 260px;
            height: 260px;
            right: -100px;
            top: -150px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(88, 225, 193, 0.14), transparent 67%);
            pointer-events: none;
        }}

        .fincent-brand-mark {{
            width: 54px;
            height: 54px;
            flex: 0 0 54px;
            display: grid;
            place-items: center;
            color: #07110F;
            background: linear-gradient(145deg, {t["primary"]}, #A8F5E3);
            border-radius: 15px;
            font-family: {t["font_mono"]};
            font-size: 1.3rem;
            font-weight: 700;
            box-shadow: 0 10px 32px rgba(88, 225, 193, 0.18);
        }}

        .fincent-header-copy {{
            min-width: 0;
            flex: 1;
        }}

        .fincent-kicker {{
            color: {t["primary"]};
            font-family: {t["font_mono"]};
            font-size: 0.68rem;
            font-weight: 600;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            margin-bottom: 0.25rem;
        }}

        .fincent-page-header h1 {{
            font-size: clamp(1.65rem, 3vw, 2.35rem);
            line-height: 1.05;
            margin: 0;
        }}

        .fincent-page-header p {{
            font-size: 0.88rem;
            line-height: 1.45;
            margin: 0.4rem 0 0;
            max-width: 760px;
        }}

        .fincent-status {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            color: #B7C2D2;
            background: rgba(7, 11, 18, 0.55);
            border: 1px solid {t["border"]};
            border-radius: 999px;
            padding: 0.48rem 0.72rem;
            font-family: {t["font_mono"]};
            font-size: 0.65rem;
            letter-spacing: 0.08em;
            white-space: nowrap;
            z-index: 1;
        }}

        .fincent-status-dot {{
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: {t["positive"]};
            box-shadow: 0 0 0 4px rgba(64, 216, 152, 0.1), 0 0 12px rgba(64, 216, 152, 0.55);
        }}

        /* Numeric displays read as terminal data, not prose. */
        [data-testid="stMetricValue"] {{
            font-family: {t["font_mono"]};
            font-weight: 600;
            color: {t["text"]};
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
            background: linear-gradient(155deg, rgba(18, 28, 42, 0.94), rgba(13, 20, 32, 0.96));
            border: 1px solid {t["border"]};
            border-radius: 14px;
            padding: 1rem 1.05rem;
            min-height: 100px;
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.14);
            position: relative;
            overflow: hidden;
        }}

        [data-testid="stMetric"]::before {{
            content: "";
            position: absolute;
            inset: 0 auto 0 0;
            width: 2px;
            background: linear-gradient({t["primary"]}, rgba(88, 225, 193, 0.05));
        }}

        code, .stCode, [data-testid="stCode"] {{
            font-family: {t["font_mono"]} !important;
        }}

        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #0D1420 0%, #090F18 100%);
            border-right: 1px solid {t["border"]};
        }}

        [data-testid="stSidebarNav"] a {{
            border-radius: 10px;
            margin: 0.15rem 0.55rem;
            padding: 0.62rem 0.8rem;
            color: #AAB5C5;
            transition: background 140ms ease, color 140ms ease;
        }}

        [data-testid="stSidebarNav"] a:hover {{
            background: rgba(88, 225, 193, 0.07);
            color: {t["text"]};
        }}

        [data-testid="stSidebarNav"] a[aria-current="page"] {{
            color: {t["text"]};
            background: linear-gradient(90deg, rgba(88, 225, 193, 0.14), rgba(88, 225, 193, 0.035));
            border: 1px solid rgba(88, 225, 193, 0.18);
        }}

        [data-testid="stSidebarNavLink"] span[label="app"] p {{
            font-size: 0;
        }}

        [data-testid="stSidebarNavLink"] span[label="app"] p::after {{
            content: "Dashboard";
            font-size: 0.875rem;
        }}

        [data-baseweb="input"],
        [data-baseweb="select"] > div,
        [data-baseweb="base-input"] {{
            background-color: rgba(13, 20, 32, 0.94) !important;
            border-color: {t["border"]} !important;
            border-radius: 11px !important;
        }}

        [data-baseweb="input"]:focus-within,
        [data-baseweb="select"] > div:focus-within {{
            border-color: rgba(88, 225, 193, 0.7) !important;
            box-shadow: 0 0 0 3px rgba(88, 225, 193, 0.08) !important;
        }}

        [data-testid="stVerticalBlockBorderWrapper"] > div,
        [data-testid="stExpander"],
        [data-testid="stDataFrame"] {{
            border: 1px solid {t["border"]} !important;
            border-radius: 13px !important;
            box-shadow: 0 12px 32px rgba(0, 0, 0, 0.12) !important;
            overflow: hidden;
        }}

        [data-testid="stPlotlyChart"] {{
            border: 1px solid {t["border"]};
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 18px 45px rgba(0, 0, 0, 0.18);
        }}

        .stAlert {{
            border: 1px solid {t["border"]};
            border-radius: 12px;
            box-shadow: none;
        }}

        button[kind="primary"] {{
            background-color: {t["primary"]};
            color: {t["background"]};
            border-radius: 10px;
            border: none;
            font-weight: 600;
            box-shadow: 0 8px 24px rgba(88, 225, 193, 0.16);
        }}
        button[kind="secondary"] {{
            border-radius: 10px;
            border: 1px solid {t["border"]};
            background: {t["surface"]};
        }}

        [data-testid="stProgress"] > div > div {{
            background-color: {t["primary"]};
        }}

        hr {{
            border-color: {t["border"]};
        }}

        @media (max-width: 760px) {{
            .block-container {{
                padding-top: 1.2rem;
            }}
            .fincent-page-header {{
                align-items: flex-start;
                padding: 1rem;
            }}
            .fincent-brand-mark {{
                width: 46px;
                height: 46px;
                flex-basis: 46px;
            }}
            .fincent-status {{
                display: none;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, kicker: str, description: str) -> None:
    """Render the branded masthead used at the top of every page."""
    st.markdown(
        f"""
        <div class="fincent-page-header">
            <div class="fincent-brand-mark">F</div>
            <div class="fincent-header-copy">
                <div class="fincent-kicker">{escape(kicker)}</div>
                <h1>{escape(title)}</h1>
                <p>{escape(description)}</p>
            </div>
            <div class="fincent-status">
                <span class="fincent-status-dot"></span>
                RESEARCH MODE
            </div>
        </div>
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
        margin=dict(l=18, r=18, t=20, b=10),
        height=420,
        paper_bgcolor=t["surface"],
        plot_bgcolor=t["surface"],
        font=dict(family=t["font_body"], color=t["text_muted"]),
        hoverlabel=dict(
            bgcolor=t["surface_alt"],
            bordercolor=t["border"],
            font=dict(color=t["text"], family=t["font_mono"]),
        ),
        xaxis=dict(gridcolor="rgba(33, 49, 72, 0.55)", showgrid=True, zeroline=False),
        yaxis=dict(gridcolor="rgba(33, 49, 72, 0.55)", showgrid=True, zeroline=False),
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
            line=dict(color=t["primary"], width=2.2),
            fill="tozeroy",
            fillcolor="rgba(88, 225, 193, 0.075)",
        )
    )
    st.plotly_chart(_themed_layout(fig), width='stretch')
