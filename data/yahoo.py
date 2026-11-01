"""Yahoo Finance fetching and parsing. Pure Python — no Streamlit.

One `.info` call per ticker produces both the quote and the fundamentals
(a "snapshot"), so the two can never drift apart and the API is hit half
as often. Caching lives in data/cache.py so this module stays importable
from scripts and tests.
"""

import logging

import pandas as pd
import yfinance as yf

from data import DataSourceError, fallback_source, fmp_source
from data.normalize import growth_fraction

logger = logging.getLogger(__name__)

SOURCE_YAHOO = "yahoo"
SOURCE_FMP = "fmp"
SOURCE_FALLBACK = "fallback"

# "auto" tries yfinance -> FMP -> chart API; the others force one source.
PROVIDER_AUTO = "auto"
PROVIDERS = (PROVIDER_AUTO, SOURCE_YAHOO, SOURCE_FMP, SOURCE_FALLBACK)

_FUND_QUOTE_TYPES = {"ETF", "MUTUALFUND"}
_EQUITY_ROWS = ("Common Stock Equity", "Stockholders Equity")

# Quote currencies that are a fraction of the reporting one: code -> (major, units per major).
_SUBUNITS = {
    "GBp": ("GBP", 100.0),
    "GBX": ("GBP", 100.0),
    "ZAc": ("ZAR", 100.0),
    "ILA": ("ILS", 100.0),
}


def _quote_from_info(ticker: str, info: dict, price: float) -> dict:
    return {
        "ticker": ticker,
        "name": info.get("longName") or ticker,
        "price": price,
        "market_cap": info.get("marketCap"),
        "currency": info.get("currency"),
    }


def _fundamentals_from_info(
    info: dict,
    price: float,
    equity: float | None = None,
    fx_rate: float | None = 1.0,
) -> dict:
    """Fundamentals in the currency the shares trade in.

    equity and the statement fields in info are in the company's reporting
    currency, and fx_rate converts them. When fx_rate is None the statement
    fields stay blank rather than mixing currencies.
    """
    # impliedSharesOutstanding covers every share class; sharesOutstanding
    # can be one class only (GOOGL, BRK-B).
    shares_outstanding = info.get("impliedSharesOutstanding") or info.get(
        "sharesOutstanding"
    )

    def converted(value: float | None) -> float | None:
        return None if value is None or fx_rate is None else value * fx_rate

    shareholder_equity = converted(equity)
    book_value_per_share = (
        shareholder_equity / shares_outstanding
        if shareholder_equity is not None and shares_outstanding
        else None
    )
    # yfinance reports dividendYield in percentage points (3.25 = 3.25%);
    # normalize to a fraction to match roe/margins.
    dividend_yield = info.get("dividendYield")
    if dividend_yield is not None:
        dividend_yield = dividend_yield / 100

    return {
        "price": price,
        "is_fund": info.get("quoteType") in _FUND_QUOTE_TYPES,
        "market_cap": info.get("marketCap"),
        "eps": info.get("trailingEps"),
        "dividend_yield": dividend_yield,
        "payout_ratio": info.get("payoutRatio"),
        "book_value_per_share": book_value_per_share,
        "net_income": converted(info.get("netIncomeToCommon")),
        "shareholder_equity": shareholder_equity,
        "total_debt": converted(info.get("totalDebt")),
        "revenue": converted(info.get("totalRevenue")),
        "free_cash_flow": converted(info.get("freeCashflow")),
        "shares_outstanding": shares_outstanding,
        "earnings_growth": growth_fraction(info.get("earningsGrowth")),
    }


def _reported_equity(stock: yf.Ticker, ticker: str) -> float | None:
    """Latest common equity from the balance sheet, in reporting currency.

    Yahoo's bookValue can be per another share class or per an underlying
    share instead of the ADR, so equity comes from the statement itself.
    """
    try:
        for sheet in (stock.quarterly_balance_sheet, stock.balance_sheet):
            for row in _EQUITY_ROWS:
                if row in sheet.index:
                    values = sheet.loc[row].dropna()
                    if not values.empty:
                        return float(values.iloc[0])
    except Exception:
        logger.warning("Balance sheet fetch failed for %s", ticker, exc_info=True)
    return None


def _fx_rate(source: str | None, target: str | None) -> float | None:
    """Multiplier from source currency to target, or None if it can't be found.

    Prices can be quoted in a subunit (BP.L trades in pence, GBp), which
    needs its own scale on top of the exchange rate.
    """
    if not source or not target or source == target:
        return 1.0
    major, scale = _SUBUNITS.get(target, (target, 1.0))
    if source == major:
        return scale
    try:
        rate = yf.Ticker(f"{source}{major}=X").fast_info["lastPrice"]
    except Exception:
        logger.warning("FX fetch failed for %s to %s", source, major, exc_info=True)
        return None
    if not rate:
        logger.warning("No FX rate for %s to %s", source, major)
        return None
    return float(rate) * scale


def _snapshot_from_yfinance(ticker: str) -> dict | None:
    """Snapshot via the yfinance library, or None if it can't deliver."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
    except Exception:
        logger.warning("yfinance .info failed for %s", ticker, exc_info=True)
        return None
    if not info:
        return None
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    if price is None:
        logger.warning("yfinance returned no price for %s", ticker)
        return None
    price = float(price)
    equity = _reported_equity(stock, ticker) if info.get("quoteType") == "EQUITY" else None
    fx_rate = _fx_rate(info.get("financialCurrency"), info.get("currency"))
    return {
        "quote": _quote_from_info(ticker, info, price),
        "fundamentals": _fundamentals_from_info(info, price, equity, fx_rate),
        "source": SOURCE_YAHOO,
    }


def _snapshot_from_chart_api(ticker: str) -> dict:
    """Price-only snapshot from Yahoo's raw chart API (no fundamentals)."""
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


def fetch_dividends(ticker: str) -> pd.Series:
    """Cash dividends from Yahoo, or an empty series when none are available."""
    try:
        series = yf.Ticker(ticker).dividends
    except Exception:
        logger.warning("Dividend fetch failed for %s", ticker, exc_info=True)
        return pd.Series(dtype=float)
    if series is None or len(series) == 0:
        return pd.Series(dtype=float)
    return series


def fetch_snapshot(ticker: str, provider: str = PROVIDER_AUTO) -> dict:
    """Quote + fundamentals from the chosen provider.

    provider="auto" falls through yfinance -> FMP -> Yahoo chart API as
    each source fails. FMP still returns full fundamentals, so DCF and
    ratios keep working during a Yahoo outage; the chart API is a last
    resort that only has price. Any other provider value forces exactly
    that source and raises DataSourceError if it can't deliver. "source"
    says which path produced the data so the UI can show it.
    """
    ticker = ticker.upper()

    if provider == SOURCE_FMP:
        return {**fmp_source.get_snapshot(ticker), "source": SOURCE_FMP}
    if provider == SOURCE_FALLBACK:
        return _snapshot_from_chart_api(ticker)

    snapshot = _snapshot_from_yfinance(ticker)
    if snapshot is not None:
        return snapshot
    if provider == SOURCE_YAHOO:
        raise DataSourceError(
            f"Yahoo Finance could not provide data for '{ticker}' — "
            "switch the data provider or try again later."
        )

    try:
        return {**fmp_source.get_snapshot(ticker), "source": SOURCE_FMP}
    except DataSourceError:
        logger.warning(
            "FMP snapshot fetch failed for %s; using chart-API fallback",
            ticker,
            exc_info=True,
        )

    return _snapshot_from_chart_api(ticker)


_OHLC_COLUMNS = ["Open", "High", "Low", "Close"]


def fetch_history(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
    provider: str = PROVIDER_AUTO,
    adjusted: bool = True,
) -> pd.DataFrame:
    """OHLC prices from the chosen provider.

    provider="auto" tries yfinance, then FMP, then the raw Yahoo chart API;
    any other value forces exactly that source. Always includes a Close
    column; Open/High/Low are included when the source provides them
    (needed for candlestick charts). adjusted=False keeps yfinance from
    marking old prices down by later dividends, which would overstate any
    past yield computed from them.
    """
    if provider == SOURCE_FMP:
        return fmp_source.get_history(ticker, period, interval)
    if provider == SOURCE_FALLBACK:
        return fallback_source.get_history(ticker, period, interval)

    try:
        df = yf.Ticker(ticker).history(
            period=period, interval=interval, auto_adjust=adjusted
        )
        if not df.empty and "Close" in df.columns:
            return df[[col for col in _OHLC_COLUMNS if col in df.columns]]
        logger.warning(
            "yfinance returned empty history for %s (%s/%s)",
            ticker,
            period,
            interval,
        )
    except Exception:
        logger.warning(
            "yfinance history failed for %s (%s/%s)",
            ticker,
            period,
            interval,
            exc_info=True,
        )

    if provider == SOURCE_YAHOO:
        raise DataSourceError(
            f"Yahoo Finance could not provide price history for '{ticker}' — "
            "switch the data provider or try again later."
        )

    try:
        return fmp_source.get_history(ticker, period, interval)
    except DataSourceError:
        logger.warning(
            "FMP history fetch failed for %s (%s/%s); using chart-API fallback",
            ticker,
            period,
            interval,
            exc_info=True,
        )

    return fallback_source.get_history(ticker, period, interval)
