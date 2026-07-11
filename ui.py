"""Shared Streamlit UI helpers used across pages."""

import streamlit as st

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
