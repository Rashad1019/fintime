import pandas as pd
import pytest

from data import DataSourceError, fallback_source, fmp_source, fx, yahoo

FULL_INFO = {
    "longName": "Apple Inc.",
    "currentPrice": 150.0,
    "marketCap": 2_500_000_000_000,
    "currency": "USD",
    "trailingEps": 6.0,
    "dividendYield": 3.25,  # yfinance reports percentage points
    "payoutRatio": 0.15,
    "bookValue": 4.0,
    "sharesOutstanding": 16_000_000_000,
    "netIncomeToCommon": 95_000_000_000,
    "totalDebt": 110_000_000_000,
    "totalRevenue": 390_000_000_000,
    "freeCashflow": 100_000_000_000,
}


def test_fundamentals_mark_funds_by_quote_type():
    assert yahoo._fundamentals_from_info(dict(FULL_INFO, quoteType="ETF"), 150.0)["is_fund"]
    assert yahoo._fundamentals_from_info(dict(FULL_INFO, quoteType="MUTUALFUND"), 150.0)["is_fund"]
    assert not yahoo._fundamentals_from_info(dict(FULL_INFO, quoteType="EQUITY"), 150.0)["is_fund"]
    assert not yahoo._fundamentals_from_info(FULL_INFO, 150.0)["is_fund"]


def test_fetch_history_passes_the_adjustment_choice_to_yfinance(monkeypatch):
    calls = []

    class FakeTicker:
        def __init__(self, ticker):
            pass

        def history(self, period, interval, auto_adjust):
            calls.append(auto_adjust)
            return pd.DataFrame({"Close": [100.0]})

    monkeypatch.setattr(yahoo.yf, "Ticker", FakeTicker)

    yahoo.fetch_history("SCHD", "5y")
    yahoo.fetch_history("SCHD", "5y", adjusted=False)

    assert calls == [True, False]


def test_fundamentals_keep_decimal_earnings_growth():
    info = dict(FULL_INFO, earningsGrowth=0.15)
    fundamentals = yahoo._fundamentals_from_info(info, 150.0)
    assert fundamentals["earnings_growth"] == pytest.approx(0.15)


def test_fundamentals_convert_percentage_point_earnings_growth():
    info = dict(FULL_INFO, earningsGrowth=15.0)
    fundamentals = yahoo._fundamentals_from_info(info, 150.0)
    assert fundamentals["earnings_growth"] == pytest.approx(0.15)


def test_fundamentals_normalizes_dividend_yield_to_fraction():
    fundamentals = yahoo._fundamentals_from_info(FULL_INFO, 150.0)
    assert fundamentals["dividend_yield"] == pytest.approx(0.0325)


def test_fundamentals_derive_book_value_from_reported_equity():
    fundamentals = yahoo._fundamentals_from_info(FULL_INFO, 150.0, equity=64e9)
    assert fundamentals["shareholder_equity"] == 64e9
    assert fundamentals["book_value_per_share"] == pytest.approx(4.0)


def test_fundamentals_count_every_share_class():
    info = dict(FULL_INFO, sharesOutstanding=5e9, impliedSharesOutstanding=12e9)
    fundamentals = yahoo._fundamentals_from_info(info, 150.0, equity=60e9)
    assert fundamentals["shares_outstanding"] == 12e9
    assert fundamentals["book_value_per_share"] == pytest.approx(5.0)


def test_fundamentals_convert_statements_to_the_trading_currency():
    fundamentals = yahoo._fundamentals_from_info(FULL_INFO, 150.0, equity=1000.0, fx_rate=0.5)
    assert fundamentals["free_cash_flow"] == 50_000_000_000
    assert fundamentals["revenue"] == 195_000_000_000
    assert fundamentals["net_income"] == 47_500_000_000
    assert fundamentals["total_debt"] == 55_000_000_000
    assert fundamentals["shareholder_equity"] == 500.0
    assert fundamentals["eps"] == 6.0


def test_fundamentals_blank_statements_without_an_fx_rate():
    fundamentals = yahoo._fundamentals_from_info(FULL_INFO, 150.0, equity=1000.0, fx_rate=None)
    assert fundamentals["free_cash_flow"] is None
    assert fundamentals["net_income"] is None
    assert fundamentals["shareholder_equity"] is None
    assert fundamentals["book_value_per_share"] is None
    assert fundamentals["price"] == 150.0
    assert fundamentals["eps"] == 6.0


def _closes(value: float) -> pd.DataFrame:
    return pd.DataFrame({"Close": [value]})


def test_fx_rate_is_one_when_currencies_match_or_are_missing():
    assert fx.rate("USD", "USD") == 1.0
    assert fx.rate(None, "USD") == 1.0


def test_fx_rate_uses_the_pair_quote(monkeypatch):
    seen = []

    def fake_history(symbol, period):
        seen.append(symbol)
        return _closes(0.03)

    monkeypatch.setattr(fallback_source, "get_history", fake_history)
    assert fx.rate("TWD", "USD") == 0.03
    assert seen == ["TWDUSD=X"]


def test_fx_rate_scales_subunit_quotes(monkeypatch):
    monkeypatch.setattr(fallback_source, "get_history", lambda symbol, period: _closes(0.03))
    assert fx.rate("GBP", "GBp") == 100.0
    assert fx.rate("USD", "GBp") == pytest.approx(3.0)


def test_fx_rate_is_none_when_the_pair_fails(monkeypatch):
    def broken(symbol, period):
        raise DataSourceError("down")

    monkeypatch.setattr(fallback_source, "get_history", broken)
    assert fx.rate("TWD", "USD") is None


def test_chart_snapshot_reads_name_currency_and_fund_type(monkeypatch):
    history = _closes(51.66)
    history.attrs["meta"] = {"longName": "NEOS Income ETF", "currency": "USD", "instrumentType": "ETF"}
    monkeypatch.setattr(fallback_source, "get_history", lambda ticker, period: history)

    snapshot = yahoo.fetch_snapshot("QQQI", yahoo.SOURCE_FALLBACK)

    assert snapshot["quote"]["name"] == "NEOS Income ETF"
    assert snapshot["quote"]["currency"] == "USD"
    filled = yahoo.fundamentals_or_price(snapshot)
    assert filled["is_fund"] is True
    assert filled["price"] == 51.66
    assert filled["eps"] is None


def test_fundamentals_or_price_returns_real_fundamentals_untouched():
    fundamentals = {"price": 10.0}
    assert yahoo.fundamentals_or_price({"fundamentals": fundamentals}) is fundamentals


def test_fetch_dividends_falls_back_to_the_chart_api(monkeypatch):
    payouts = pd.Series([1.0], index=pd.to_datetime(["2026-01-01"]))
    monkeypatch.setattr(yahoo.yf, "Ticker", _BrokenTicker)
    monkeypatch.setattr(fallback_source, "get_dividends", lambda ticker: payouts)
    assert yahoo.fetch_dividends("QQQI").equals(payouts)


def test_fetch_dividends_is_empty_when_every_source_fails(monkeypatch):
    def broken(ticker):
        raise DataSourceError("down")

    monkeypatch.setattr(yahoo.yf, "Ticker", _BrokenTicker)
    monkeypatch.setattr(fallback_source, "get_dividends", broken)
    assert len(yahoo.fetch_dividends("QQQI")) == 0


def test_chart_dividends_parse_events_in_date_order(monkeypatch):
    payload = {"chart": {"result": [{"events": {"dividends": {
        "2": {"amount": 0.5, "date": 1_700_000_000},
        "1": {"amount": 0.4, "date": 1_690_000_000},
    }}}]}}
    monkeypatch.setattr(
        fallback_source.requests, "get", lambda *a, **kw: _FakeChartResponse(payload)
    )
    assert fallback_source.get_dividends("QQQI").tolist() == [0.4, 0.5]


def test_chart_dividends_are_empty_for_a_non_payer(monkeypatch):
    payload = {"chart": {"result": [{}]}}
    monkeypatch.setattr(
        fallback_source.requests, "get", lambda *a, **kw: _FakeChartResponse(payload)
    )
    assert len(fallback_source.get_dividends("TSLA")) == 0


class _SheetTicker:
    def __init__(self, quarterly, annual):
        self.quarterly_balance_sheet = quarterly
        self.balance_sheet = annual


def _sheet(row: str, values: list) -> pd.DataFrame:
    return pd.DataFrame([values], index=[row])


def test_reported_equity_prefers_the_latest_quarter():
    stock = _SheetTicker(_sheet("Common Stock Equity", [5.0, 4.0]), _sheet("Common Stock Equity", [3.0]))
    assert yahoo._reported_equity(stock, "X") == 5.0


def test_reported_equity_falls_back_to_annual_and_skips_blanks():
    stock = _SheetTicker(pd.DataFrame(), _sheet("Stockholders Equity", [float("nan"), 3.0]))
    assert yahoo._reported_equity(stock, "X") == 3.0


def test_reported_equity_is_none_when_the_sheet_fails():
    class Broken:
        @property
        def quarterly_balance_sheet(self):
            raise RuntimeError("down")

    assert yahoo._reported_equity(Broken(), "X") is None


def test_fundamentals_missing_fields_are_none():
    fundamentals = yahoo._fundamentals_from_info({"currentPrice": 30.0}, 30.0)
    assert fundamentals["eps"] is None
    assert fundamentals["dividend_yield"] is None
    assert fundamentals["shareholder_equity"] is None


def test_quote_name_falls_back_to_ticker():
    quote = yahoo._quote_from_info("XYZ", {"currentPrice": 10.0}, 10.0)
    assert quote["name"] == "XYZ"


class _BrokenTicker:
    def __init__(self, symbol):
        pass

    @property
    def info(self):
        raise RuntimeError("yfinance is down")


def test_snapshot_degrades_to_fmp_when_yfinance_fails(monkeypatch):
    monkeypatch.setattr(yahoo.yf, "Ticker", _BrokenTicker)
    fmp_snapshot = {
        "quote": {"ticker": "AAPL", "name": "Apple Inc.", "price": 150.0, "market_cap": 1, "currency": "USD"},
        "fundamentals": {"price": 150.0, "eps": 6.0},
    }
    monkeypatch.setattr(
        yahoo.fmp_source, "get_snapshot", lambda ticker: fmp_snapshot
    )

    snapshot = yahoo.fetch_snapshot("aapl")

    assert snapshot["source"] == yahoo.SOURCE_FMP
    assert snapshot["fundamentals"]["eps"] == 6.0
    assert snapshot["quote"]["price"] == 150.0


def test_snapshot_degrades_to_chart_fallback_when_yfinance_and_fmp_fail(monkeypatch):
    monkeypatch.setattr(yahoo.yf, "Ticker", _BrokenTicker)
    monkeypatch.setattr(
        yahoo.fmp_source,
        "get_snapshot",
        lambda ticker: (_ for _ in ()).throw(DataSourceError("FMP down")),
    )
    fallback_df = pd.DataFrame(
        {"Close": [100.0, 101.5]}, index=pd.to_datetime(["2026-07-01", "2026-07-02"])
    )
    monkeypatch.setattr(
        yahoo.fallback_source, "get_history", lambda ticker, period: fallback_df
    )

    snapshot = yahoo.fetch_snapshot("aapl")

    assert snapshot["source"] == yahoo.SOURCE_FALLBACK
    assert snapshot["fundamentals"] is None
    assert snapshot["quote"]["ticker"] == "AAPL"
    assert snapshot["quote"]["price"] == 101.5


def test_history_degrades_to_fmp_when_yfinance_fails(monkeypatch):
    class _BrokenHistoryTicker:
        def __init__(self, symbol):
            pass

        def history(self, period, interval):
            raise RuntimeError("yfinance is down")

    monkeypatch.setattr(yahoo.yf, "Ticker", _BrokenHistoryTicker)
    fmp_df = pd.DataFrame({"Close": [200.0]}, index=pd.to_datetime(["2026-07-10"]))
    monkeypatch.setattr(
        yahoo.fmp_source, "get_history", lambda ticker, period, interval: fmp_df
    )

    df = yahoo.fetch_history("aapl")

    assert list(df["Close"]) == [200.0]


def test_history_degrades_to_chart_fallback_when_yfinance_and_fmp_fail(monkeypatch):
    class _BrokenHistoryTicker:
        def __init__(self, symbol):
            pass

        def history(self, period, interval):
            raise RuntimeError("yfinance is down")

    monkeypatch.setattr(yahoo.yf, "Ticker", _BrokenHistoryTicker)
    monkeypatch.setattr(
        yahoo.fmp_source,
        "get_history",
        lambda ticker, period, interval: (_ for _ in ()).throw(DataSourceError("FMP down")),
    )
    fallback_df = pd.DataFrame({"Close": [100.0]}, index=pd.to_datetime(["2026-07-01"]))
    monkeypatch.setattr(
        yahoo.fallback_source, "get_history", lambda ticker, period, interval: fallback_df
    )

    df = yahoo.fetch_history("aapl")

    assert list(df["Close"]) == [100.0]


def test_forced_yahoo_provider_raises_instead_of_falling_back(monkeypatch):
    monkeypatch.setattr(yahoo.yf, "Ticker", _BrokenTicker)
    monkeypatch.setattr(
        yahoo.fmp_source,
        "get_snapshot",
        lambda ticker: pytest.fail("FMP must not be called when Yahoo is forced"),
    )

    with pytest.raises(DataSourceError, match="Yahoo Finance"):
        yahoo.fetch_snapshot("AAPL", provider=yahoo.SOURCE_YAHOO)


def test_forced_fmp_provider_skips_yfinance(monkeypatch):
    monkeypatch.setattr(
        yahoo.yf,
        "Ticker",
        lambda symbol: pytest.fail("yfinance must not be called when FMP is forced"),
    )
    fmp_snapshot = {
        "quote": {"ticker": "AAPL", "name": "Apple Inc.", "price": 150.0, "market_cap": 1, "currency": "USD"},
        "fundamentals": {"price": 150.0},
    }
    monkeypatch.setattr(yahoo.fmp_source, "get_snapshot", lambda ticker: fmp_snapshot)

    snapshot = yahoo.fetch_snapshot("AAPL", provider=yahoo.SOURCE_FMP)

    assert snapshot["source"] == yahoo.SOURCE_FMP


def test_forced_backup_provider_returns_price_only_snapshot(monkeypatch):
    monkeypatch.setattr(
        yahoo.yf,
        "Ticker",
        lambda symbol: pytest.fail("yfinance must not be called when backup is forced"),
    )
    fallback_df = pd.DataFrame({"Close": [100.0]}, index=pd.to_datetime(["2026-07-01"]))
    monkeypatch.setattr(
        yahoo.fallback_source, "get_history", lambda ticker, period: fallback_df
    )

    snapshot = yahoo.fetch_snapshot("AAPL", provider=yahoo.SOURCE_FALLBACK)

    assert snapshot["source"] == yahoo.SOURCE_FALLBACK
    assert snapshot["fundamentals"] is None


def test_forced_yahoo_history_raises_instead_of_falling_back(monkeypatch):
    class _BrokenHistoryTicker:
        def __init__(self, symbol):
            pass

        def history(self, period, interval):
            raise RuntimeError("yfinance is down")

    monkeypatch.setattr(yahoo.yf, "Ticker", _BrokenHistoryTicker)

    with pytest.raises(DataSourceError, match="Yahoo Finance"):
        yahoo.fetch_history("AAPL", provider=yahoo.SOURCE_YAHOO)


class _FakeChartResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_fallback_parses_chart_payload(monkeypatch):
    payload = {
        "chart": {
            "result": [
                {
                    "timestamp": [1751328000, 1751414400],
                    "indicators": {"quote": [{"close": [100.0, None]}]},
                }
            ]
        }
    }
    monkeypatch.setattr(
        fallback_source.requests, "get", lambda *a, **kw: _FakeChartResponse(payload)
    )
    df = fallback_source.get_history("AAPL", "1mo")
    assert list(df["Close"]) == [100.0]  # None rows dropped


def test_fallback_parses_ohlc_for_candlesticks(monkeypatch):
    payload = {
        "chart": {
            "result": [
                {
                    "timestamp": [1751328000],
                    "indicators": {
                        "quote": [
                            {
                                "open": [99.0],
                                "high": [102.0],
                                "low": [98.5],
                                "close": [100.0],
                            }
                        ]
                    },
                }
            ]
        }
    }
    monkeypatch.setattr(
        fallback_source.requests, "get", lambda *a, **kw: _FakeChartResponse(payload)
    )
    df = fallback_source.get_history("AAPL", "1d", "5m")
    assert list(df.columns) == ["Open", "High", "Low", "Close"]
    assert df["High"].iloc[0] == 102.0


def test_fallback_invalid_period_and_interval_use_safe_defaults(monkeypatch):
    captured = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        captured.update(params)
        return _FakeChartResponse(
            {
                "chart": {
                    "result": [
                        {
                            "timestamp": [1751328000],
                            "indicators": {"quote": [{"close": [100.0]}]},
                        }
                    ]
                }
            }
        )

    monkeypatch.setattr(fallback_source.requests, "get", fake_get)
    fallback_source.get_history("AAPL", "bogus", "bogus")
    assert captured == {"range": "1y", "interval": "1d"}


def test_fallback_malformed_payload_raises(monkeypatch):
    monkeypatch.setattr(
        fallback_source.requests,
        "get",
        lambda *a, **kw: _FakeChartResponse({"chart": {"result": None}}),
    )
    with pytest.raises(DataSourceError, match="AAPL"):
        fallback_source.get_history("AAPL", "1mo")


def test_profile_reads_a_fund_from_yfinance(monkeypatch):
    class FakeTicker:
        info = {
            "longName": "iShares Core S&P 500 ETF",
            "quoteType": "ETF",
            "longBusinessSummary": "Tracks the S&P 500.",
            "fundFamily": "iShares",
            "netExpenseRatio": 0.03,
        }

        def __init__(self, symbol):
            pass

    monkeypatch.setattr(yahoo.yf, "Ticker", FakeTicker)

    profile = yahoo.fetch_profile("ivv")

    assert profile["name"] == "iShares Core S&P 500 ETF"
    assert profile["kind"] == "ETF"
    assert profile["family"] == "iShares"
    assert profile["expense_ratio"] == pytest.approx(0.0003)


def test_profile_falls_back_to_fmp(monkeypatch):
    monkeypatch.setattr(yahoo.yf, "Ticker", _BrokenTicker)
    monkeypatch.setattr(fmp_source, "get_profile", lambda ticker: {"name": "From FMP"})
    assert yahoo.fetch_profile("IVV") == {"name": "From FMP"}


def test_profile_falls_back_to_the_chart_api(monkeypatch):
    def no_fmp(ticker):
        raise DataSourceError("down")

    history = pd.DataFrame({"Close": [1.0]})
    history.attrs["meta"] = {"longName": "iShares Core S&P 500 ETF", "instrumentType": "ETF"}
    monkeypatch.setattr(yahoo.yf, "Ticker", _BrokenTicker)
    monkeypatch.setattr(fmp_source, "get_profile", no_fmp)
    monkeypatch.setattr(fallback_source, "get_history", lambda ticker, period: history)

    profile = yahoo.fetch_profile("IVV")

    assert profile["name"] == "iShares Core S&P 500 ETF"
    assert profile["kind"] == "ETF"
    assert profile["summary"] is None
