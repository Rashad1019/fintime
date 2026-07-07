"""Streamlit-cached facade over data.yahoo — the only data module pages import.

Keeps st.cache_data out of the pure fetching layer so scripts and tests can
use data.yahoo without a Streamlit runtime.
"""

import logging
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import streamlit as st

from data import DataSourceError, yahoo

logger = logging.getLogger(__name__)

QUOTE_TTL_SECONDS = 300
HISTORY_TTL_SECONDS = 900
_MAX_PARALLEL_FETCHES = 8


@st.cache_data(ttl=QUOTE_TTL_SECONDS, show_spinner=False)
def get_snapshot(ticker: str) -> dict:
    """Cached quote + fundamentals for one ticker (see yahoo.fetch_snapshot)."""
    return yahoo.fetch_snapshot(ticker)


@st.cache_data(ttl=HISTORY_TTL_SECONDS, show_spinner=False)
def get_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Cached daily close prices."""
    return yahoo.fetch_history(ticker, period)


def _snapshot_or_none(ticker: str) -> dict | None:
    try:
        return yahoo.fetch_snapshot(ticker)
    except DataSourceError:
        logger.warning("Snapshot fetch failed for %s", ticker, exc_info=True)
        return None


@st.cache_data(ttl=QUOTE_TTL_SECONDS, show_spinner=False)
def get_snapshots(tickers: tuple[str, ...]) -> dict[str, dict | None]:
    """Snapshots for a whole watchlist, fetched in parallel.

    Workers run only pure data.yahoo code (no Streamlit calls in threads).
    A ticker that fails maps to None instead of sinking the whole page.
    """
    if not tickers:
        return {}
    workers = min(_MAX_PARALLEL_FETCHES, len(tickers))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = pool.map(_snapshot_or_none, tickers)
    return dict(zip(tickers, results))
