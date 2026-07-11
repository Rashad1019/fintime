"""Backup data source: Financial Modeling Prep (FMP).

Used when both yfinance and the Yahoo chart-API fallback are unavailable.
Unlike the chart-API fallback, FMP provides full fundamentals (income
statement, balance sheet, cash flow, ratios), so DCF and valuation ratios
keep working during a Yahoo outage.

Requires FMP_API_KEY in .env — sign up free at
https://site.financialmodelingprep.com/developer/docs
"""

import datetime
import logging
import os

import pandas as pd
import requests
from dotenv import load_dotenv

from data import DataSourceError

load_dotenv()

logger = logging.getLogger(__name__)

BASE_URL = "https://financialmodelingprep.com/stable"
REQUEST_TIMEOUT_SECONDS = 30

# config.HISTORY_PERIODS ranges -> approximate calendar-day lookback.
_PERIOD_LOOKBACK_DAYS = {
    "1d": 3,
    "5d": 8,
    "1mo": 32,
    "3mo": 95,
    "6mo": 189,
    "1y": 369,
    "2y": 734,
    "5y": 1830,
}
_MAX_LOOKBACK_START = datetime.date(1990, 1, 1)

# config.HISTORY_PERIODS intervals -> FMP's historical-chart interval names.
_INTRADAY_INTERVAL_MAP = {
    "1m": "1min",
    "2m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "60m": "1hour",
}

_OHLC_RENAME = {"open": "Open", "high": "High", "low": "Low", "close": "Close"}
_OHLC_COLUMNS = ["Open", "High", "Low", "Close"]


def _api_key() -> str:
    key = os.getenv("FMP_API_KEY")
    if not key:
        raise DataSourceError(
            "FMP_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return key


def _get(path: str, params: dict) -> list | dict:
    try:
        response = requests.get(
            f"{BASE_URL}/{path}",
            params={**params, "apikey": _api_key()},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except DataSourceError:
        raise
    except requests.HTTPError as exc:
        raise DataSourceError(
            f"FMP request to '{path}' failed: HTTP {exc.response.status_code}"
        ) from exc
    except requests.RequestException as exc:
        # Don't interpolate `exc` — urllib3 connection errors embed the
        # full request URL, including the apikey query param, and this
        # message gets logged (data.yahoo logs FMP failures with exc_info).
        raise DataSourceError(
            f"FMP request to '{path}' failed: {type(exc).__name__}"
        ) from exc

    if isinstance(payload, dict) and "Error Message" in payload:
        raise DataSourceError(f"FMP error: {payload['Error Message'][:200]}")
    return payload


def _first(path: str, symbol: str, **params) -> dict:
    payload = _get(path, {"symbol": symbol, **params})
    if not payload:
        raise DataSourceError(f"FMP has no {path} data for '{symbol}'")
    return payload[0]


def get_snapshot(ticker: str) -> dict:
    """Quote + fundamentals from FMP, shaped like data.yahoo.fetch_snapshot's dict.

    Returns {"quote": ..., "fundamentals": ...} — no "source" key; the
    caller (data.yahoo) stamps that on so this module stays a plain source.
    """
    ticker = ticker.upper()
    try:
        profile = _first("profile", ticker)
        income = _first("income-statement", ticker, limit=1)
        balance = _first("balance-sheet-statement", ticker, limit=1)
        cash_flow = _first("cash-flow-statement", ticker, limit=1)
        ratios = _first("ratios", ticker, limit=1)

        price = profile.get("price")
        if price is None:
            raise DataSourceError(f"FMP has no price for '{ticker}'")
        price = float(price)

        quote = {
            "ticker": ticker,
            "name": profile.get("companyName") or ticker,
            "price": price,
            "market_cap": profile.get("marketCap"),
            "currency": profile.get("currency"),
        }
        fundamentals = {
            "price": price,
            "market_cap": profile.get("marketCap"),
            "eps": income.get("eps"),
            "dividend_yield": ratios.get("dividendYield"),
            "payout_ratio": ratios.get("dividendPayoutRatio"),
            "book_value_per_share": ratios.get("bookValuePerShare"),
            "net_income": income.get("netIncome"),
            "shareholder_equity": balance.get("totalStockholdersEquity"),
            "total_debt": balance.get("totalDebt"),
            "revenue": income.get("revenue"),
            "free_cash_flow": cash_flow.get("freeCashFlow"),
            "shares_outstanding": income.get("weightedAverageShsOut"),
        }
    except DataSourceError:
        raise
    except Exception as exc:
        raise DataSourceError(f"FMP snapshot fetch failed for '{ticker}': {exc}") from exc

    return {"quote": quote, "fundamentals": fundamentals}


def _date_range(period: str) -> tuple[str, str]:
    today = datetime.date.today()
    if period == "max":
        return _MAX_LOOKBACK_START.isoformat(), today.isoformat()
    days = _PERIOD_LOOKBACK_DAYS.get(period, 369)
    return (today - datetime.timedelta(days=days)).isoformat(), today.isoformat()


def get_history(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """OHLC prices from FMP's EOD or intraday chart endpoints."""
    ticker = ticker.upper()
    from_date, to_date = _date_range(period)
    fmp_interval = _INTRADAY_INTERVAL_MAP.get(interval)
    path = f"historical-chart/{fmp_interval}" if fmp_interval else "historical-price-eod/full"

    try:
        rows = _get(path, {"symbol": ticker, "from": from_date, "to": to_date})
        if not rows:
            raise DataSourceError(f"FMP has no price history for '{ticker}'")

        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index().rename(columns=_OHLC_RENAME)
        df = df[_OHLC_COLUMNS]
    except DataSourceError:
        raise
    except Exception as exc:
        raise DataSourceError(f"FMP history fetch failed for '{ticker}': {exc}") from exc

    return df
