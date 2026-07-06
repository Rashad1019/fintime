"""Risk metrics computed from a price series as pure functions."""

import math

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def _daily_returns(prices: pd.Series) -> pd.Series:
    prices = pd.Series(prices, dtype=float).dropna()
    if len(prices) < 2:
        raise ValueError("need at least 2 prices to compute returns")
    return prices.pct_change().dropna()


def annualized_volatility(prices: pd.Series) -> float:
    """Sample standard deviation of daily returns, annualized."""
    returns = _daily_returns(prices)
    return float(returns.std(ddof=1) * math.sqrt(TRADING_DAYS_PER_YEAR))


def sharpe_ratio(prices: pd.Series, risk_free_rate: float = 0.0) -> float | None:
    """Annualized Sharpe ratio. None when volatility is zero (undefined)."""
    returns = _daily_returns(prices)
    volatility = float(returns.std(ddof=1) * math.sqrt(TRADING_DAYS_PER_YEAR))
    if volatility == 0.0:
        return None
    annual_return = float(returns.mean()) * TRADING_DAYS_PER_YEAR
    return (annual_return - risk_free_rate) / volatility


def historical_var(prices: pd.Series, confidence: float = 0.95) -> float:
    """Historical value-at-risk of daily returns.

    Returns a positive number: the loss (as a fraction) not exceeded with
    the given confidence on a single day.
    """
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    returns = _daily_returns(prices)
    percentile = (1 - confidence) * 100
    return float(-np.percentile(returns, percentile))
