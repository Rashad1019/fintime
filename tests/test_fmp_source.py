import pandas as pd
import pytest

from data import DataSourceError, fmp_source


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        pass


def _mock_get(monkeypatch, responses: dict):
    """responses maps the FMP path (e.g. "profile") to its payload."""

    def fake_get(url, params=None, timeout=None):
        for path, payload in responses.items():
            if url.endswith(path):
                return _FakeResponse(payload)
        raise AssertionError(f"Unexpected URL in test: {url}")

    monkeypatch.setattr(fmp_source.requests, "get", fake_get)


PROFILE = [{"companyName": "Apple Inc.", "price": 150.0, "marketCap": 2_500_000_000_000, "currency": "USD"}]
INCOME = [{"eps": 6.0, "netIncome": 95_000_000_000, "revenue": 390_000_000_000, "weightedAverageShsOut": 16_000_000_000}]
BALANCE = [{"totalStockholdersEquity": 64_000_000_000, "totalDebt": 110_000_000_000}]
CASH_FLOW = [{"freeCashFlow": 100_000_000_000}]
RATIOS = [{"dividendYield": 0.0325, "dividendPayoutRatio": 0.15, "bookValuePerShare": 4.0}]


def test_get_snapshot_maps_all_fields(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    _mock_get(
        monkeypatch,
        {
            "profile": PROFILE,
            "income-statement": INCOME,
            "balance-sheet-statement": BALANCE,
            "cash-flow-statement": CASH_FLOW,
            "ratios": RATIOS,
        },
    )

    snapshot = fmp_source.get_snapshot("aapl")

    assert snapshot["quote"] == {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "price": 150.0,
        "market_cap": 2_500_000_000_000,
        "currency": "USD",
    }
    fundamentals = snapshot["fundamentals"]
    assert fundamentals["eps"] == 6.0
    assert fundamentals["dividend_yield"] == 0.0325
    assert fundamentals["shareholder_equity"] == 64_000_000_000
    assert fundamentals["free_cash_flow"] == 100_000_000_000
    assert fundamentals["shares_outstanding"] == 16_000_000_000


def test_get_snapshot_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    with pytest.raises(DataSourceError, match="FMP_API_KEY"):
        fmp_source.get_snapshot("AAPL")


def test_get_snapshot_raises_on_missing_price(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    _mock_get(
        monkeypatch,
        {
            "profile": [{"companyName": "Apple Inc.", "marketCap": 1}],
            "income-statement": INCOME,
            "balance-sheet-statement": BALANCE,
            "cash-flow-statement": CASH_FLOW,
            "ratios": RATIOS,
        },
    )
    with pytest.raises(DataSourceError, match="AAPL"):
        fmp_source.get_snapshot("AAPL")


def test_get_snapshot_raises_on_empty_payload(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    _mock_get(monkeypatch, {"profile": []})
    with pytest.raises(DataSourceError, match="profile"):
        fmp_source.get_snapshot("AAPL")


def test_get_snapshot_raises_on_fmp_error_message(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "bad-key")
    _mock_get(monkeypatch, {"profile": {"Error Message": "Invalid API KEY."}})
    with pytest.raises(DataSourceError, match="Invalid API KEY"):
        fmp_source.get_snapshot("AAPL")


def test_get_history_daily_parses_eod_rows(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    _mock_get(
        monkeypatch,
        {
            "historical-price-eod/full": [
                {"date": "2026-07-10", "open": 314.72, "high": 316.91, "low": 312.17, "close": 315.32},
                {"date": "2026-07-09", "open": 310.51, "high": 316.53, "low": 308.16, "close": 316.22},
            ]
        },
    )

    df = fmp_source.get_history("AAPL", "1mo", "1d")

    assert list(df.columns) == ["Open", "High", "Low", "Close"]
    assert list(df.index) == sorted(df.index)  # ascending, oldest first
    assert df["Close"].iloc[-1] == 315.32


def test_get_history_intraday_uses_chart_endpoint(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    _mock_get(
        monkeypatch,
        {
            "historical-chart/5min": [
                {"date": "2026-07-10 15:55:00", "open": 316.12, "low": 314.78, "high": 316.18, "close": 315.33},
            ]
        },
    )

    df = fmp_source.get_history("AAPL", "1d", "5m")

    assert df["Close"].iloc[0] == 315.33


def test_get_history_raises_on_empty_rows(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    _mock_get(monkeypatch, {"historical-price-eod/full": []})
    with pytest.raises(DataSourceError, match="AAPL"):
        fmp_source.get_history("AAPL")


def test_get_snapshot_connection_error_does_not_leak_api_key(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "super-secret-key")

    def raise_connection_error(url, params=None, timeout=None):
        raise fmp_source.requests.exceptions.ConnectionError(
            f"Failed to connect: url with apikey=super-secret-key"
        )

    monkeypatch.setattr(fmp_source.requests, "get", raise_connection_error)

    with pytest.raises(DataSourceError) as exc_info:
        fmp_source.get_snapshot("AAPL")
    assert "super-secret-key" not in str(exc_info.value)


def test_get_history_raises_data_source_error_on_malformed_row(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    _mock_get(
        monkeypatch,
        {"historical-price-eod/full": [{"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0}]},
    )  # missing "date" key
    with pytest.raises(DataSourceError, match="AAPL"):
        fmp_source.get_history("AAPL")


def test_date_range_handles_max_period():
    start, end = fmp_source._date_range("max")
    assert start == "1990-01-01"
    assert end == pd.Timestamp.today().date().isoformat()
