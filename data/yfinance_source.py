"""Primary data source: Yahoo Finance via yfinance, with a direct
chart-API fallback for price data. Results are cached so Streamlit
reruns don't re-hit the API.
"""

import pandas as pd
import streamlit as st
import yfinance as yf

from data import DataSourceError, fallback_source

QUOTE_TTL_SECONDS = 300
HISTORY_TTL_SECONDS = 900
FUNDAMENTALS_TTL_SECONDS = 3600


@st.cache_data(ttl=QUOTE_TTL_SECONDS, show_spinner=False)
def get_quote(ticker: str) -> dict:
    """Current price and identity for a ticker. Falls back to the last close."""
    ticker = ticker.upper()
    try:
        info = yf.Ticker(ticker).info
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if price is not None:
            return {
                "ticker": ticker,
                "name": info.get("longName") or ticker,
                "price": float(price),
                "market_cap": info.get("marketCap"),
                "currency": info.get("currency"),
            }
    except Exception:
        pass  # fall through to the fallback source

    history = fallback_source.get_history(ticker, period="1mo")
    return {
        "ticker": ticker,
        "name": ticker,
        "price": float(history["Close"].iloc[-1]),
        "market_cap": None,
        "currency": None,
    }


@st.cache_data(ttl=HISTORY_TTL_SECONDS, show_spinner=False)
def get_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Daily close prices. Tries the yfinance library first, then the raw chart API."""
    try:
        df = yf.Ticker(ticker).history(period=period)
        if not df.empty and "Close" in df.columns:
            return df[["Close"]]
    except Exception:
        pass  # fall through to the fallback source

    return fallback_source.get_history(ticker, period)


@st.cache_data(ttl=FUNDAMENTALS_TTL_SECONDS, show_spinner=False)
def get_fundamentals(ticker: str) -> dict:
    """Fundamentals needed by analytics/. No fallback source exists for these."""
    ticker = ticker.upper()
    try:
        info = yf.Ticker(ticker).info
    except Exception as exc:
        raise DataSourceError(
            f"Could not fetch fundamentals for '{ticker}': {exc}"
        ) from exc

    price = info.get("currentPrice") or info.get("regularMarketPrice")
    if price is None:
        raise DataSourceError(f"Yahoo Finance has no fundamentals for '{ticker}'")

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
        "price": float(price),
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
