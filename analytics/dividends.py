"""Trailing dividend-yield range from prices and a dividend series."""

import pandas as pd


def dividend_yield_range(
    prices: pd.Series | None, dividends: pd.Series | None
) -> dict | None:
    """Low and high trailing-twelve-month yield over the price history.

    Yield on each day is the dividends paid in the prior 365 days divided
    by that day's price. Returns None when there is not enough history to
    call it a range.
    """
    if prices is None or dividends is None or len(prices) < 2 or len(dividends) == 0:
        return None

    prices = _normalize_index(prices)
    dividends = _normalize_index(dividends)
    prices = prices[~prices.index.duplicated(keep="last")].sort_index()
    dividends = dividends.groupby(level=0).sum().sort_index()

    calendar = prices.index.union(dividends.index).sort_values()
    prices = prices.reindex(calendar).ffill()
    paid = dividends.reindex(calendar, fill_value=0.0)
    trailing = paid.rolling("365D").sum()
    yields = (trailing / prices).replace([float("inf"), float("-inf")], pd.NA).dropna()
    positive = yields[yields > 0]
    if len(positive) < 30:
        return None
    return {
        "dividend_yield_low": float(positive.min()),
        "dividend_yield_high": float(positive.max()),
    }


def _normalize_index(series: pd.Series) -> pd.Series:
    series = series.copy()
    index = pd.to_datetime(series.index, utc=True).tz_convert(None).normalize()
    series.index = index
    return series
