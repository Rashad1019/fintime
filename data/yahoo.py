"""Yahoo Finance fetching and parsing. Pure Python — no Streamlit.

One `.info` call per ticker produces both the quote and the fundamentals
(a "snapshot"), so the two can never drift apart and the API is hit half
as often. Caching lives in data/cache.py so this module stays importable
from scripts and tests.
"""

import logging

import pandas as pd
import yfinance as yf

from data import fallback_source

logger = logging.getLogger(__name__)

SOURCE_YAHOO = "yahoo"
SOURCE_FALLBACK = "fallback"


def _quote_from_info(ticker: str, info: dict, price: float) -> dict:
    return {
        "ticker": ticker,
        "name": info.get("longName") or ticker,
        "price": price,
        "market_cap": info.get("marketCap"),
        "currency": info.get("currency"),
    }


def _fundamentals_from_info(info: dict, price: float) -> dict:
    book_value_per_share = info.get("bookValue")
    shares_outstanding = info.get("sharesOutstanding")
    shareholder_equity = (
        book_value_per_share * shares_outstanding
        if book_value_per_share is not None and shares_outstanding is not None
        else None
    )
    # yfinance reports dividendYield in percentage points (3.25 = 3.25%);
    # normalize to a fraction to match roe/margins.
    dividend_yield = info.get("dividendYield")
    if dividend_yield is not None:
        dividend_yield = dividend_yield / 100

    return {
        "price": price,
        "market_cap": info.get("marketCap"),
        "eps": info.get("trailingEps"),
        "dividend_yield": dividend_yield,
        "payout_ratio": info.get("payoutRatio"),
        "book_value_per_share": book_value_per_share,
        "net_income": info.get("netIncomeToCommon"),
        "shareholder_equity": shareholder_equity,
        "total_debt": info.get("totalDebt"),
        "revenue": info.get("totalRevenue"),
        "free_cash_flow": info.get("freeCashflow"),
        "shares_outstanding": shares_outstanding,
    }


def fetch_snapshot(ticker: str) -> dict:
    """Quote + fundamentals from a single .info call.

    Always returns a usable quote — degrading to the chart API's last close
    when yfinance fails. "fundamentals" is None on the degraded path, and
    "source" says which path produced the data so the UI can show it.

    Raises DataSourceError only when the fallback also fails.
    """
    ticker = ticker.upper()
    info = None
    try:
        info = yf.Ticker(ticker).info
    except Exception:
        logger.warning(
            "yfinance .info failed for %s; using chart-API fallback",
            ticker,
            exc_info=True,
        )

    if info:
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if price is not None:
            price = float(price)
            return {
                "quote": _quote_from_info(ticker, info, price),
                "fundamentals": _fundamentals_from_info(info, price),
                "source": SOURCE_YAHOO,
            }
        logger.warning(
            "yfinance returned no price for %s; using chart-API fallback", ticker
        )

    history = fallback_source.get_history(ticker, period="1mo")
    return {
        "quote": {
            "ticker": ticker,
            "name": ticker,
            "price": float(history["Close"].iloc[-1]),
            "market_cap": None,
            "currency": None,
        },
        "fundamentals": None,
        "source": SOURCE_FALLBACK,
    }


_OHLC_COLUMNS = ["Open", "High", "Low", "Close"]


def fetch_history(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """OHLC prices. Tries the yfinance library first, then the raw chart API.

    Always includes a Close column; Open/High/Low are included when the
    source provides them (needed for candlestick charts).
    """
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval)
        if not df.empty and "Close" in df.columns:
            return df[[col for col in _OHLC_COLUMNS if col in df.columns]]
        logger.warning(
            "yfinance returned empty history for %s (%s/%s); using chart-API fallback",
            ticker,
            period,
            interval,
        )
    except Exception:
        logger.warning(
            "yfinance history failed for %s (%s/%s); using chart-API fallback",
            ticker,
            period,
            interval,
            exc_info=True,
        )
    return fallback_source.get_history(ticker, period, interval)
