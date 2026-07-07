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

_VALID_RANGES = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"}
_VALID_INTERVALS = {"1m", "2m", "5m", "15m", "30m", "60m", "1d"}

_OHLC_FIELDS = {"Open": "open", "High": "high", "Low": "low", "Close": "close"}


def get_history(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """OHLC prices from Yahoo's chart endpoint."""
    if period not in _VALID_RANGES:
        period = "1y"
    if interval not in _VALID_INTERVALS:
        interval = "1d"
    try:
        response = requests.get(
            CHART_URL.format(symbol=ticker.upper()),
            params={"range": period, "interval": interval},
            headers=_HEADERS,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        payload = response.json()
        result = payload["chart"]["result"][0]
        timestamps = result["timestamp"]
        quote = result["indicators"]["quote"][0]
        columns = {
            name: quote[field] for name, field in _OHLC_FIELDS.items() if field in quote
        }
        if "Close" not in columns:
            raise KeyError("close")
    except Exception as exc:
        raise DataSourceError(
            f"Fallback price fetch failed for '{ticker}': {exc}"
        ) from exc

    df = pd.DataFrame(columns, index=pd.to_datetime(timestamps, unit="s")).dropna(
        subset=["Close"]
    )
    if df.empty:
        raise DataSourceError(f"Fallback source has no price data for '{ticker}'")
    return df
