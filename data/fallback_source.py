"""Fallback price source: Yahoo Finance's public chart API, called directly.

Used when the yfinance library fails (parsing breakage, .info errors,
version churn). Hits the raw JSON endpoint with plain requests so price
history keeps working even if the library itself breaks. No API key needed.
"""

import pandas as pd
import requests

from data import DataSourceError

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
_HEADERS = {"User-Agent": "Mozilla/5.0"}
REQUEST_TIMEOUT_SECONDS = 30

_VALID_RANGES = {"1mo", "3mo", "6mo", "1y", "2y", "5y", "max"}


def get_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Daily close prices from Yahoo's chart endpoint."""
    if period not in _VALID_RANGES:
        period = "1y"
    try:
        response = requests.get(
            CHART_URL.format(symbol=ticker.upper()),
            params={"range": period, "interval": "1d"},
            headers=_HEADERS,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        payload = response.json()
        result = payload["chart"]["result"][0]
        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
    except Exception as exc:
        raise DataSourceError(
            f"Fallback price fetch failed for '{ticker}': {exc}"
        ) from exc

    df = pd.DataFrame(
        {"Close": closes}, index=pd.to_datetime(timestamps, unit="s")
    ).dropna()
    if df.empty:
        raise DataSourceError(f"Fallback source has no price data for '{ticker}'")
    return df
