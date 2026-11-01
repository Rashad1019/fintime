import pandas as pd
import pytest

from agents.metrics import assemble_metrics
from agents.verdicts import parse_verdict, without_verdict
from analytics.dividends import dividend_yield_range, trailing_yield
from data import DataSourceError, fallback_source, macro
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
        "VERDICT: WAIT | conviction 4\n"
        "VERDICT: SKIP | conviction 8"
    )
    assert parse_verdict(text) == ("Skip", 8)


def test_parse_verdict_reads_buy_now_and_a_bare_buy():
    assert parse_verdict("VERDICT: BUY NOW | conviction 7") == ("Buy now", 7)
    assert parse_verdict("VERDICT: buy | conviction 7") == ("Buy now", 7)


def test_without_verdict_removes_the_line_readers_should_not_see():
    reply = "**My take:** Fine.\n\n**VERDICT: WAIT | conviction 6**"
    assert without_verdict(reply) == "**My take:** Fine."


def test_parse_verdict_rejects_a_score_outside_one_to_ten():
    assert parse_verdict("VERDICT: WAIT | conviction 12") == ("Wait", None)
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
    months = pd.date_range("2025-01-01", periods=13, freq="MS")
    cpi = pd.Series([100.0] * 12 + [103.0], index=months)
    assert inflation_yoy(cpi) == pytest.approx(0.03)
    assert inflation_yoy(cpi.iloc[:2]) is None
    assert inflation_yoy(None) is None


def test_inflation_yoy_is_not_stretched_by_a_missing_month():
    months = pd.date_range("2024-09-01", periods=25, freq="MS")
    cpi = pd.Series([float(100 + i) for i in range(25)], index=months)
    cpi = cpi.drop(pd.Timestamp("2025-10-01"))

    assert inflation_yoy(cpi) == pytest.approx(124 / 112 - 1)


def test_inflation_yoy_steps_back_when_the_year_ago_month_is_missing():
    months = pd.date_range("2024-09-01", periods=26, freq="MS")
    cpi = pd.Series([float(100 + i) for i in range(26)], index=months)
    cpi = cpi.drop(pd.Timestamp("2025-10-01"))

    assert inflation_yoy(cpi) == pytest.approx(124 / 112 - 1)


def test_bls_series_skips_annual_averages_and_missing_months():
    rows = [
        {"year": "2026", "period": "M01", "value": "325.2"},
        {"year": "2025", "period": "M13", "value": "321.9"},
        {"year": "2025", "period": "M12", "value": "324.0"},
        {"year": "2025", "period": "M10", "value": "-"},
    ]

    series = macro._bls_series(rows)

    assert series.to_dict() == {
        pd.Timestamp("2025-12-01"): 324.0,
        pd.Timestamp("2026-01-01"): 325.2,
    }


def test_chart_ten_year_converts_percentage_points(monkeypatch):
    monkeypatch.setattr(
        fallback_source, "get_history", lambda symbol, period: pd.DataFrame({"Close": [4.93]})
    )
    assert macro._chart_ten_year() == pytest.approx(0.0493)


def test_fetch_macro_falls_back_to_fred(monkeypatch):
    def broken_chart(symbol, period):
        raise DataSourceError("down")

    months = pd.date_range("2025-01-01", periods=13, freq="MS")
    series = {
        "DGS10": pd.Series([4.0]),
        "CPIAUCSL": pd.Series([100.0] * 12 + [102.0], index=months),
    }
    monkeypatch.setattr(fallback_source, "get_history", broken_chart)
    monkeypatch.setattr(macro, "_read_bls_cpi", lambda: None)
    monkeypatch.setattr(macro, "_read_fred", series.get)

    result = macro.fetch_macro()

    assert result["ten_year_yield"] == pytest.approx(0.04)
    assert result["inflation_yoy"] == pytest.approx(0.02)


def test_fetch_macro_is_none_when_every_source_fails(monkeypatch):
    def broken_chart(symbol, period):
        raise DataSourceError("down")

    monkeypatch.setattr(fallback_source, "get_history", broken_chart)
    monkeypatch.setattr(macro, "_read_bls_cpi", lambda: None)
    monkeypatch.setattr(macro, "_read_fred", lambda series_id: None)

    assert macro.fetch_macro() == {"ten_year_yield": None, "inflation_yoy": None}
