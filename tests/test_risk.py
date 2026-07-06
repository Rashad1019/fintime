import math

import numpy as np
import pandas as pd
import pytest

from analytics.risk import annualized_volatility, historical_var, sharpe_ratio


def test_constant_prices_have_zero_volatility():
    prices = pd.Series([100.0] * 30)
    assert annualized_volatility(prices) == 0.0


def test_volatility_hand_computed():
    # Returns: +10%, -10%. Sample std (ddof=1) = 0.1414..., annualized x sqrt(252).
    prices = pd.Series([100.0, 110.0, 99.0])
    expected = np.std([0.10, -0.10], ddof=1) * math.sqrt(252)
    assert annualized_volatility(prices) == pytest.approx(expected)


def test_volatility_requires_at_least_two_prices():
    with pytest.raises(ValueError):
        annualized_volatility(pd.Series([100.0]))
    with pytest.raises(ValueError):
        annualized_volatility(pd.Series([], dtype=float))


def test_sharpe_ratio_zero_volatility_returns_none():
    prices = pd.Series([100.0] * 30)
    assert sharpe_ratio(prices) is None


def test_sharpe_ratio_positive_for_steady_gains():
    # Steadily rising prices with slight noise -> positive Sharpe.
    rng = np.random.default_rng(42)
    returns = 0.001 + rng.normal(0, 0.0001, 100)
    prices = pd.Series(100.0 * np.cumprod(1 + returns))
    assert sharpe_ratio(prices) > 0


def test_historical_var_hand_computed():
    returns = np.array([-0.05, -0.02, -0.01, 0.0, 0.01, 0.01, 0.02, 0.02, 0.03, 0.04])
    prices = pd.Series(100.0 * np.cumprod(np.concatenate(([1.0], 1 + returns))))
    expected = -np.percentile(returns, 5)
    assert historical_var(prices, confidence=0.95) == pytest.approx(expected)


def test_historical_var_is_positive_for_losses():
    prices = pd.Series([100.0, 90.0, 95.0, 85.0, 88.0, 80.0])
    assert historical_var(prices, confidence=0.95) > 0
