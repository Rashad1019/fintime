"""Shared Streamlit UI helpers used across pages.

Visual identity: "Black Ledger" — editorial, restrained market intelligence.
Palette and fonts are defined once in THEME/apply_theme() so every page
stays visually consistent; call ui.apply_theme() right after
st.set_page_config() on every page.
"""

from base64 import b64encode
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import INTRADAY_WINDOW_HOURS
from data import yahoo

# Single source of truth for the palette — reused by CSS injection and by
# the Plotly chart colors so charts match the chrome around them.
THEME = {
    "background": "#050505",
    "surface": "#0B0B0D",
    "surface_alt": "#111115",
    "border": "#2A2A30",
    "primary": "#8E96FF",
    "secondary": "#446DFF",
    "text": "#F7F7F4",
    "text_muted": "#99999F",
    "positive": "#4BD49B",
    "negative": "#F26D7D",
    "font_body": "'Manrope', sans-serif",
    "font_mono": "'IBM Plex Mono', monospace",
}

_GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Manrope:wght@400;500;600;700&"
    "family=IBM+Plex+Mono:wght@400;500&display=swap"
)


def apply_theme() -> None:
    """Inject the restrained Black Ledger visual system."""
    t = THEME
    st.markdown(
        f"""
        <style>
        @import url('{_GOOGLE_FONTS_URL}');

        html, body, [class*="css"] {{ font-family: {t["font_body"]}; }}
        .stApp, [data-testid="stAppViewContainer"] {{ background: {t["background"]}; }}
        [data-testid="stHeader"] {{
            background: rgba(5, 5, 5, 0.86);
            border-bottom: 1px solid {t["border"]};
            backdrop-filter: blur(18px);
        }}
        [data-testid="stAppViewContainer"] {{ color: {t["text"]}; }}
        .block-container {{ max-width: 1380px; padding-top: 1.7rem; padding-bottom: 5rem; }}

        h1, h2, h3, h4 {{
            color: {t["text"]};
            font-family: {t["font_body"]};
            font-weight: 500;
            letter-spacing: -0.045em;
        }}
        h2 {{ font-size: 1.35rem; margin-top: 2rem; }}
        p, label, [data-testid="stCaptionContainer"] {{ color: {t["text_muted"]}; }}

        .fincent-page-header {{ margin-bottom: 2.25rem; }}
        .fincent-section-header {{
            padding: 2rem 0 1.6rem;
            border-top: 1px solid {t["border"]};
            border-bottom: 1px solid {t["border"]};
        }}
        .fincent-header-copy {{ max-width: 900px; position: relative; z-index: 1; }}
        .fincent-kicker {{
            color: #B9B9C0;
            font-family: {t["font_mono"]};
            font-size: 0.64rem;
            font-weight: 500;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            margin-bottom: 0.75rem;
        }}
        .fincent-section-header h1 {{
            font-size: clamp(2.8rem, 5.5vw, 5.6rem);
            line-height: 0.98;
            margin: 0;
        }}
        .fincent-section-header p {{
            max-width: 640px;
            font-size: 0.9rem;
            line-height: 1.6;
            margin: 0.9rem 0 0;
        }}

        .fincent-home-hero {{
            min-height: 570px;
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
            padding: 2.2rem 2.6rem 2.7rem;
            border: 1px solid #202026;
            background-color: #000;
            background-size: cover;
            background-position: center;
            position: relative;
            overflow: hidden;
        }}
        .fincent-wordmark {{
            position: absolute;
            left: 2.6rem;
            top: 2rem;
            display: flex;
            align-items: center;
            gap: 0.55rem;
            color: #fff;
            font-size: 1.05rem;
            font-weight: 650;
            letter-spacing: -0.04em;
        }}
        .fincent-wordmark-symbol {{
            width: 15px;
            height: 15px;
            border: 1.5px solid #fff;
            border-radius: 50%;
            display: inline-block;
            position: relative;
        }}
        .fincent-wordmark-symbol::after {{
            content: "";
            position: absolute;
            top: -2px;
            bottom: -2px;
            left: 50%;
            border-left: 1.5px solid #fff;
            transform: rotate(24deg);
        }}
        .fincent-home-hero h1 {{
            color: #fff;
            font-size: clamp(3.4rem, 7.6vw, 7.4rem);
            line-height: 0.88;
            letter-spacing: -0.075em;
            margin: 0;
            max-width: 950px;
        }}
        .fincent-home-hero p {{
            color: #B8B8BE;
            max-width: 560px;
            font-size: 0.92rem;
            line-height: 1.65;
            margin: 1.45rem 0 0;
        }}

        [data-testid="stMetric"] {{
            min-height: 96px;
            padding: 1rem 0;
            background: transparent;
            border-top: 1px solid {t["border"]};
            border-bottom: 1px solid {t["border"]};
            border-radius: 0;
        }}
        [data-testid="stMetricValue"] {{
            color: {t["text"]};
            font-family: {t["font_mono"]};
            font-weight: 400;
        }}
        [data-testid="stMetricLabel"] {{
            color: {t["text_muted"]};
            font-size: 0.68rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
        }}
        [data-testid="stMetricDelta"], code, .stCode, [data-testid="stCode"] {{
            font-family: {t["font_mono"]} !important;
        }}

        [data-testid="stSidebar"] {{
            background: #080809;
            border-right: 1px solid {t["border"]};
        }}
        [data-testid="stSidebarNav"] a {{
            color: #94949B;
            margin: 0;
            padding: 0.72rem 1.2rem;
            border-left: 2px solid transparent;
            border-radius: 0;
            font-size: 0.72rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }}
        [data-testid="stSidebarNav"] a:hover {{ color: #fff; background: transparent; }}
        [data-testid="stSidebarNav"] a[aria-current="page"] {{
            color: #fff;
            background: transparent;
            border-left-color: {t["primary"]};
        }}
        [data-testid="stSidebarNavLink"] span[label="app"] p {{ font-size: 0; }}
        [data-testid="stSidebarNavLink"] span[label="app"] p::after {{
            content: "Dashboard";
            font-size: 0.72rem;
        }}

        [data-baseweb="input"], [data-baseweb="select"] > div,
        [data-baseweb="base-input"] {{
            background-color: #0A0A0C !important;
            border-color: #34343A !important;
            border-radius: 2px !important;
        }}
        [data-baseweb="input"]:focus-within,
        [data-baseweb="select"] > div:focus-within {{
            border-color: {t["primary"]} !important;
            box-shadow: none !important;
        }}
        [data-testid="stVerticalBlockBorderWrapper"] > div,
        [data-testid="stExpander"], [data-testid="stDataFrame"] {{
            border: 1px solid {t["border"]} !important;
            border-radius: 2px !important;
            box-shadow: none !important;
        }}
        [data-testid="stPlotlyChart"] {{
            border: 1px solid {t["border"]};
            border-radius: 0;
            overflow: hidden;
        }}
        .stAlert {{ border: 1px solid {t["border"]}; border-radius: 2px; }}

        button[kind="primary"] {{
            background: #F5F5F2;
            color: #050505;
            border: 0;
            border-radius: 999px;
            padding-left: 1.25rem;
            padding-right: 1.25rem;
            font-weight: 650;
            box-shadow: none;
        }}
        button[kind="secondary"] {{
            color: #E7E7E4;
            background: transparent;
            border: 1px solid {t["border"]};
            border-radius: 999px;
        }}
        [data-testid="stProgress"] > div > div {{ background-color: {t["primary"]}; }}
        hr {{ border-color: {t["border"]}; }}

        @media (max-width: 760px) {{
            .block-container {{ padding-top: 1rem; }}
            .fincent-home-hero {{
                min-height: 500px;
                padding: 1.25rem 1.25rem 1.7rem;
                background-position: 58% center;
            }}
            .fincent-wordmark {{ left: 1.25rem; top: 1.2rem; }}
            .fincent-home-hero h1 {{ font-size: clamp(3rem, 16vw, 5rem); }}
            .fincent-section-header {{ padding: 1.35rem 0; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _hero_data_uri() -> str:
    asset = Path(__file__).resolve().parent / "assets" / "fincent-hero.png"
    payload = b64encode(asset.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{payload}"


def page_header(
    title: str, kicker: str, description: str, *, hero: bool = False
) -> None:
    """Render an editorial hero on the dashboard or a restrained page heading."""
    headline = "<br>".join(escape(line) for line in title.split("\n"))
    if hero:
        background = (
            "linear-gradient(90deg, rgba(0,0,0,.98) 0%, rgba(0,0,0,.82) 35%, "
            "rgba(0,0,0,.08) 72%), "
            f"url('{_hero_data_uri()}')"
        )
        st.markdown(
            f"""
            <div class="fincent-page-header fincent-home-hero" style="background-image:{background}">
                <div class="fincent-wordmark">
                    <span class="fincent-wordmark-symbol"></span> fincent
                </div>
                <div class="fincent-header-copy">
                    <div class="fincent-kicker">{escape(kicker)}</div>
                    <h1>{headline}</h1>
                    <p>{escape(description)}</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f"""
        <div class="fincent-page-header fincent-section-header">
            <div class="fincent-header-copy">
                <div class="fincent-kicker">{escape(kicker)}</div>
                <h1>{headline}</h1>
                <p>{escape(description)}</p>
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
            fillcolor="rgba(92, 111, 255, 0.09)",
        )
    )
    st.plotly_chart(_themed_layout(fig), width='stretch')
