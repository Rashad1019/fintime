import pandas as pd
import pytest

from data import DataSourceError, fallback_source, yahoo

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


def test_fundamentals_normalizes_dividend_yield_to_fraction():
    fundamentals = yahoo._fundamentals_from_info(FULL_INFO, 150.0)
    assert fundamentals["dividend_yield"] == pytest.approx(0.0325)


def test_fundamentals_derives_shareholder_equity():
    fundamentals = yahoo._fundamentals_from_info(FULL_INFO, 150.0)
    assert fundamentals["shareholder_equity"] == 4.0 * 16_000_000_000


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


def test_snapshot_degrades_to_fallback_when_yfinance_fails(monkeypatch):
    monkeypatch.setattr(yahoo.yf, "Ticker", _BrokenTicker)
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
