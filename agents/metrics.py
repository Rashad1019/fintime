"""Assemble the number block the personas actually see."""

import pandas as pd

from analytics.dcf import dcf_value
from analytics.dividends import dividend_yield_range
from analytics.ratios import compute_ratios, peg_ratio
from analytics import technicals
from analytics.risk import annualized_volatility, historical_var, sharpe_ratio
from config import (
    DCF_DISCOUNT,
    DCF_GROWTH,
    DCF_SLOW_GROWTH,
    DCF_STRESS_DISCOUNT,
    DCF_TERMINAL_GROWTH,
    DCF_YEARS,
)


def assemble_metrics(
    fundamentals: dict,
    prices: pd.Series,
    dividends: pd.Series | None = None,
    macro: dict | None = None,
    dividend_prices: pd.Series | None = None,
) -> dict:
    """Ratios, two DCF cases, risk, technicals, and the extra context fields."""
    metrics = {
        "price": fundamentals.get("price"),
        "market_cap": fundamentals.get("market_cap"),
        "eps": fundamentals.get("eps"),
        "dividend_yield": fundamentals.get("dividend_yield"),
        "payout_ratio": fundamentals.get("payout_ratio"),
        "revenue": fundamentals.get("revenue"),
        "net_income": fundamentals.get("net_income"),
        "free_cash_flow": fundamentals.get("free_cash_flow"),
        "earnings_growth": fundamentals.get("earnings_growth"),
        **compute_ratios(fundamentals),
    }
    metrics["peg_ratio"] = peg_ratio(metrics.get("pe_ratio"), metrics.get("earnings_growth"))

    per_share = _per_share_dcf(
        fundamentals.get("free_cash_flow"),
        fundamentals.get("shares_outstanding"),
        DCF_GROWTH,
        DCF_DISCOUNT,
    )
    slow = _per_share_dcf(
        fundamentals.get("free_cash_flow"),
        fundamentals.get("shares_outstanding"),
        DCF_SLOW_GROWTH,
        DCF_STRESS_DISCOUNT,
    )
    metrics["dcf_value_per_share"] = per_share
    metrics["dcf_conservative_per_share"] = slow

    try:
        metrics["annualized_volatility"] = annualized_volatility(prices)
        metrics["sharpe_ratio"] = sharpe_ratio(prices)
        metrics["historical_var_95"] = historical_var(prices)
    except ValueError:
        metrics["annualized_volatility"] = None
        metrics["sharpe_ratio"] = None
        metrics["historical_var_95"] = None

    summary = technicals.build_summary(prices)
    verdict = technicals.sentiment(summary)
    metrics["rsi_14"] = summary["rsi_14"]
    metrics["return_1mo"] = summary["return_1mo"]
    metrics["technical_sentiment"] = f"{verdict['label']} (score {verdict['score']:+d})"

    yield_range = dividend_yield_range(
        prices if dividend_prices is None else dividend_prices, dividends
    )
    metrics["dividend_yield_low"] = (
        None if yield_range is None else yield_range["dividend_yield_low"]
    )
    metrics["dividend_yield_high"] = (
        None if yield_range is None else yield_range["dividend_yield_high"]
    )

    macro = macro or {}
    metrics["ten_year_yield"] = macro.get("ten_year_yield")
    metrics["inflation_yoy"] = macro.get("inflation_yoy")
    return metrics


def _per_share_dcf(fcf, shares, growth: float, discount: float) -> float | None:
    if not fcf or not shares:
        return None
    total = dcf_value(fcf, growth, discount, DCF_TERMINAL_GROWTH, DCF_YEARS)
    return total / shares
