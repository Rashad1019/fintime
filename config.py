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
    "4h": ("1d", "5m"),
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

# Sub-day periods share a full-day fetch; slice to the last N hours of bars.
INTRADAY_WINDOW_HOURS = {"1h": 1, "4h": 4}

# Timeframes offered on the front-page dashboard chart.
DASHBOARD_PERIODS = ["1h", "4h", "1d", "1wk", "1mo", "1y"]

# Per-timeframe RSI basis: timeframe -> (range, interval, resample, bar label).
# Trader convention: "4H RSI" means RSI-14 on 4-hour candles, so each
# timeframe fetches enough of its own bar size (resampling when the source
# has no native interval for it). 1y uses daily bars — the convention for
# long horizons.
RSI_TIMEFRAMES = {
    "1h": ("1mo", "60m", None, "1-hour"),
    "4h": ("3mo", "60m", "4h", "4-hour"),
    "1d": ("1y", "1d", None, "daily"),
    "1wk": ("5y", "1d", "W", "weekly"),
    "1mo": ("5y", "1d", "ME", "monthly"),
    "1y": ("1y", "1d", None, "daily"),
}

# Period used for risk metrics (volatility, Sharpe, VaR) — daily bars.
RISK_HISTORY_PERIOD = "1y"
