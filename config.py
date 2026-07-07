"""Shared app constants — the single source of truth for the pages.

Change a DCF assumption here and every page (Analytics, Agents) sees it.
"""

# Default DCF assumptions (fractions, not percents).
DCF_GROWTH = 0.08
DCF_DISCOUNT = 0.10
DCF_TERMINAL_GROWTH = 0.025
DCF_YEARS = 5

# Chart periods offered in the UI: label -> (Yahoo chart range, bar interval).
# Intraday ranges need intraday bars; Yahoo serves 1m data for ~7 days only.
HISTORY_PERIODS = {
    "1h": ("1d", "1m"),
    "1d": ("1d", "5m"),
    "1wk": ("5d", "15m"),
    "1mo": ("1mo", "1d"),
    "3mo": ("3mo", "1d"),
    "6mo": ("6mo", "1d"),
    "1y": ("1y", "1d"),
    "2y": ("2y", "1d"),
    "5y": ("5y", "1d"),
}
DEFAULT_PERIOD = "1y"

# Period used for risk metrics (volatility, Sharpe, VaR) — daily bars.
RISK_HISTORY_PERIOD = "1y"
