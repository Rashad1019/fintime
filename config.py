"""Shared app constants — the single source of truth for the pages.

Change a DCF assumption here and every page (Analytics, Agents) sees it.
"""

# Default DCF assumptions (fractions, not percents).
DCF_GROWTH = 0.08
DCF_DISCOUNT = 0.10
DCF_TERMINAL_GROWTH = 0.025
DCF_YEARS = 5

# Chart periods offered in the UI (must be valid Yahoo chart-API ranges).
HISTORY_PERIODS = ["1mo", "3mo", "6mo", "1y", "2y", "5y"]

# Period used for risk metrics (volatility, Sharpe, VaR).
RISK_HISTORY_PERIOD = "1y"
