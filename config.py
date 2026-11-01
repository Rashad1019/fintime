"""Shared app constants — the single source of truth for the pages.

Change a DCF assumption here and every page (Analytics, Agents) sees it.
"""

# Default DCF assumptions (fractions, not percents).
DCF_GROWTH = 0.08
DCF_DISCOUNT = 0.10
DCF_TERMINAL_GROWTH = 0.025
DCF_YEARS = 5
# Second case for the agent prompt: slower growth and a higher required return.
DCF_SLOW_GROWTH = 0.04
DCF_STRESS_DISCOUNT = 0.12

# Chart timeframes offered in the UI: label -> (Yahoo chart range, bar interval).
HISTORY_PERIODS = {
    "1 day": ("1d", "5m"),
    "1 week": ("5d", "15m"),
    "1 month": ("1mo", "1d"),
    "3 months": ("3mo", "1d"),
    "6 months": ("6mo", "1d"),
    "1 year": ("1y", "1d"),
    "5 years": ("5y", "1d"),
}
DEFAULT_PERIOD = "1 month"

# Period used for risk metrics (volatility, Sharpe, VaR) — daily bars.
RISK_HISTORY_PERIOD = "1y"
