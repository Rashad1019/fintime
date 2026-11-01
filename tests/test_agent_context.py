import pandas as pd
import pytest

from agents.metrics import assemble_metrics
from agents.verdicts import parse_verdict
from analytics.dividends import dividend_yield_range, trailing_yield
from data.macro import inflation_yoy

AS_OF = pd.Timestamp("2026-10-31")


def _monthly_payouts(amount: float, months: int) -> pd.Series:
    dates = pd.date_range(end="2026-10-28", periods=months, freq="MS", tz="America/New_York")
    return pd.Series(amount, index=dates)


def _payouts_to_today(amount: float, count: int, days: int) -> pd.Series:
    today = pd.Timestamp.now().normalize()
    return pd.Series(amount, index=pd.date_range(end=today, periods=count, freq=f"{days}D"))


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
    dates = pd.date_range("2020-01-01", periods=600, freq="D")
    prices = pd.Series([100.0] * 450 + [50.0] * 150, index=dates)
    dividends = pd.Series(1.0, index=dates[::91])

    result = dividend_yield_range(prices, dividends)

    assert result["dividend_yield_low"] == 0.04
    assert result["dividend_yield_high"] == 0.08


def test_dividend_yield_range_ignores_days_after_payouts_stop():
    dates = pd.date_range("2020-01-01", periods=1400, freq="D")
    prices = pd.Series([100.0] * 1000 + [10.0] * 400, index=dates)
    dividends = pd.Series(1.0, index=dates[:500][::91])

    result = dividend_yield_range(prices, dividends)

    assert result["dividend_yield_high"] == 0.04


def test_dividend_yield_range_skips_the_partial_first_year():
    dates = pd.date_range("2020-01-01", periods=730, freq="D")
    prices = pd.Series(100.0, index=dates)
    dividends = pd.Series(1.0, index=dates[::30])

    result = dividend_yield_range(prices, dividends)

    assert result["dividend_yield_low"] >= 0.11


def test_dividend_yield_range_is_none_for_a_fund_under_a_year_old():
    dates = pd.date_range("2020-01-01", periods=300, freq="D")
    prices = pd.Series(100.0, index=dates)
    dividends = pd.Series(1.0, index=dates[::30])

    assert dividend_yield_range(prices, dividends) is None


def test_dividend_yield_range_counts_four_payouts_for_a_drifting_quarterly_payer():
    dates = pd.date_range("2020-01-01", periods=1100, freq="D")
    prices = pd.Series(100.0, index=dates)
    dividends = pd.Series(1.0, index=dates[::88])

    result = dividend_yield_range(prices, dividends)

    assert result["dividend_yield_high"] == 0.04


def test_trailing_yield_counts_only_the_last_year():
    payouts = _monthly_payouts(0.5, 24)
    assert trailing_yield(50.0, payouts, as_of=AS_OF) == pytest.approx(0.12)


def test_trailing_yield_keeps_every_payout_late_in_the_pay_cycle():
    payouts = _monthly_payouts(0.5, 24)
    quarterly = pd.Series(1.0, index=pd.date_range(end="2026-08-01", periods=8, freq="91D"))
    assert trailing_yield(50.0, payouts, as_of=AS_OF) == pytest.approx(0.12)
    assert trailing_yield(100.0, quarterly, as_of=AS_OF) == pytest.approx(0.04)


def test_trailing_yield_needs_a_full_year_of_history():
    assert trailing_yield(50.0, _monthly_payouts(0.5, 6), as_of=AS_OF) is None


def test_trailing_yield_is_none_when_payouts_stopped_or_price_missing():
    payouts = _monthly_payouts(0.5, 24)
    assert trailing_yield(50.0, payouts, as_of=AS_OF + pd.DateOffset(years=2)) is None
    assert trailing_yield(None, payouts, as_of=AS_OF) is None
    assert trailing_yield(50.0, pd.Series(dtype=float), as_of=AS_OF) is None


@pytest.mark.parametrize(
    "reported, is_fund, expected",
    [
        (0.0011, True, 0.12),  # fund: always payouts
        (0.11, True, 0.12),
        (0.0011, False, 0.12),  # stock with a bad field
        (None, False, 0.12),  # stock with no field
        (0.10, False, 0.10),  # stock in line: keep the forward yield
        (0.03, False, 0.03),  # special dividend: 4x apart is not an error
    ],
)
def test_assemble_metrics_checks_yield_against_payouts(reported, is_fund, expected):
    prices = pd.Series([float(100 + i) for i in range(260)])
    fundamentals = {"price": 100.0, "dividend_yield": reported, "is_fund": is_fund}

    metrics = assemble_metrics(fundamentals, prices, _payouts_to_today(1.0, 24, 30))

    assert metrics["dividend_yield"] == pytest.approx(expected)
    assert metrics["dividend_yield_paid"] == pytest.approx(0.12)


def test_assemble_metrics_keeps_reported_yield_without_payouts():
    prices = pd.Series([float(100 + i) for i in range(260)])
    fundamentals = {"price": 100.0, "dividend_yield": 0.03, "is_fund": True}

    metrics = assemble_metrics(fundamentals, prices)

    assert metrics["dividend_yield"] == 0.03
    assert metrics["dividend_yield_paid"] is None


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
