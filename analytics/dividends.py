"""Trailing dividend-yield range from prices and a dividend series."""

import pandas as pd

# Measured back from a payout date, so twelve monthly or four quarterly payouts
# fit, and slightly under a year so a drifting quarterly payer can't land five.
TRAILING_WINDOW_DAYS = 350
# A payer that has been quiet this long has stopped; annual dates can drift.
STOPPED_AFTER_DAYS = 380


def dividend_yield_range(
    prices: pd.Series | None, dividends: pd.Series | None
) -> dict | None:
    """Low and high trailing-twelve-month yield over the price history.

    Yield on each day is the year of dividends up to the latest payout divided
    by that day's price. Days inside the first year of payouts are skipped,
    since a partial year of dividends understates the yield. Prices must be
    raw closes: dividend-adjusted ones overstate past yields. Returns None
    when there is not enough history to call it a range.
    """
    if prices is None or dividends is None or len(prices) < 2 or len(dividends) == 0:
        return None

    prices = _normalize_index(prices)
    dividends = _normalize_index(dividends)
    prices = prices[~prices.index.duplicated(keep="last")].sort_index()
    dividends = dividends.groupby(level=0).sum().sort_index()

    calendar = prices.index.union(dividends.index).sort_values()
    prices = prices.reindex(calendar).ffill()
    trailing = dividends.rolling(f"{TRAILING_WINDOW_DAYS}D").sum().reindex(calendar).ffill()
    last_paid = pd.Series(dividends.index, index=dividends.index).reindex(calendar).ffill()
    trailing = trailing[(calendar - last_paid) <= pd.Timedelta(days=STOPPED_AFTER_DAYS)]
    yields = (trailing / prices).replace([float("inf"), float("-inf")], pd.NA).dropna()
    full_year_from = dividends.index.min() + pd.Timedelta(days=365)
    positive = yields[(yields > 0) & (yields.index >= full_year_from)]
    if len(positive) < 30:
        return None
    return {
        "dividend_yield_low": float(positive.min()),
        "dividend_yield_high": float(positive.max()),
    }


def trailing_yield(
    price: float | None,
    dividends: pd.Series | None,
    as_of: pd.Timestamp | None = None,
) -> float | None:
    """The year of dividends up to the latest payout, divided by price.

    Returns None without a price, when payouts have stopped, or when the
    payout history is shorter than a year, since a partial year understates
    the yield.
    """
    if not price or price <= 0 or dividends is None or len(dividends) == 0:
        return None

    dividends = _normalize_index(dividends)
    end = pd.Timestamp.now() if as_of is None else as_of
    dividends = dividends[dividends.index <= end]
    if dividends.empty or dividends.index.min() > end - pd.Timedelta(days=365):
        return None
    latest = dividends.index.max()
    if end - latest > pd.Timedelta(days=STOPPED_AFTER_DAYS):
        return None
    paid = dividends[dividends.index > latest - pd.Timedelta(days=TRAILING_WINDOW_DAYS)].sum()
    return float(paid / price) if paid > 0 else None


def _normalize_index(series: pd.Series) -> pd.Series:
    series = series.copy()
    index = pd.to_datetime(series.index, utc=True).tz_convert(None).normalize()
    series.index = index
    return series
