import pandas as pd
import pytest

from agents.metrics import assemble_metrics
from agents.verdicts import parse_verdict
from analytics.dividends import dividend_yield_range
from data.macro import inflation_yoy


def test_parse_verdict_uses_the_last_structured_line():
    text = (
        "A passing mention of BUY is not the verdict.\n"
        "VERDICT: HOLD | conviction 4\n"
        "VERDICT: AVOID | conviction 8"
    )
    assert parse_verdict(text) == ("AVOID", 8)


def test_parse_verdict_rejects_a_score_outside_one_to_ten():
    assert parse_verdict("VERDICT: BUY | conviction 12") == ("BUY", None)
    assert parse_verdict("no verdict here") == (None, None)


def test_dividend_yield_range_uses_trailing_twelve_months():
    dates = pd.date_range("2020-01-01", periods=400, freq="D")
    prices = pd.Series(100.0, index=dates)
    dividends = pd.Series([1.0, 1.0], index=[dates[10], dates[200]])

    result = dividend_yield_range(prices, dividends)

    assert result["dividend_yield_low"] == 0.01
    assert result["dividend_yield_high"] == 0.02


def test_dividend_yield_range_needs_a_real_history():
    prices = pd.Series([100.0], index=pd.to_datetime(["2020-01-01"]))
    dividends = pd.Series([1.0], index=pd.to_datetime(["2020-01-01"]))
    assert dividend_yield_range(prices, dividends) is None


def test_assemble_metrics_includes_peg_and_both_dcf_cases():
    fundamentals = {
        "price": 100.0,
        "market_cap": 1_000.0,
        "eps": 5.0,
        "dividend_yield": 0.02,
        "payout_ratio": 0.3,
        "revenue": 10.0,
        "net_income": 2.0,
        "free_cash_flow": 100.0,
        "shares_outstanding": 10.0,
        "earnings_growth": 0.10,
        "book_value_per_share": 20.0,
        "shareholder_equity": 50.0,
        "total_debt": 10.0,
    }
    prices = pd.Series([float(100 + i) for i in range(260)])

    metrics = assemble_metrics(
        fundamentals,
        prices,
        macro={"ten_year_yield": 0.04, "inflation_yoy": 0.03},
    )

    assert metrics["peg_ratio"] == pytest.approx(2.0)
    assert metrics["dcf_value_per_share"] > metrics["dcf_conservative_per_share"]
    assert metrics["ten_year_yield"] == 0.04
    assert metrics["dividend_yield_low"] is None


def test_inflation_yoy_compares_with_twelve_months_earlier():
    cpi = pd.Series([100.0] * 12 + [103.0])
    assert inflation_yoy(cpi) == pytest.approx(0.03)
    assert inflation_yoy(pd.Series([100.0, 101.0])) is None
