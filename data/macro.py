"""Public macro series used by the agent prompt. No API key.

Each series has a second source, because hosted apps can be blocked from any
one of them. Failures stay local: a missing series comes back as None and the
persona prompt shows N/A instead of sinking the analysis.
"""

import io
import logging
import urllib.request

import pandas as pd
import requests

from data import DataSourceError, fallback_source

logger = logging.getLogger(__name__)

_FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
_BLS_CPI = "https://api.bls.gov/publicAPI/v1/timeseries/data/CUUR0000SA0"
_TEN_YEAR_INDEX = "^TNX"
_TIMEOUT_SECONDS = 15


def fetch_macro() -> dict:
    """10-year Treasury yield and year-over-year CPI, as fractions."""
    cpi = _read_bls_cpi()
    return {
        "ten_year_yield": _chart_ten_year() or _ten_year_yield(_read_fred("DGS10")),
        "inflation_yoy": inflation_yoy(cpi if cpi is not None else _read_fred("CPIAUCSL")),
    }


def inflation_yoy(cpi: pd.Series | None) -> float | None:
    """Change in the latest monthly CPI that has a reading a year earlier.

    cpi is indexed by month. Matching on dates rather than position keeps a
    month missing from the source (October 2025) from stretching the span.
    """
    if cpi is None:
        return None
    for month in reversed(cpi.index):
        year_ago = month - pd.DateOffset(years=1)
        if year_ago in cpi.index and cpi[year_ago] != 0:
            return float(cpi[month]) / float(cpi[year_ago]) - 1
    return None


def _ten_year_yield(yields: pd.Series | None) -> float | None:
    """FRED quotes DGS10 in percentage points (4.25 = 4.25%)."""
    if yields is None or len(yields) == 0:
        return None
    return float(yields.iloc[-1]) / 100


def _chart_ten_year() -> float | None:
    """Yahoo's ^TNX index, also quoted in percentage points."""
    try:
        history = fallback_source.get_history(_TEN_YEAR_INDEX, period="5d")
    except DataSourceError:
        logger.warning("Chart fetch failed for %s", _TEN_YEAR_INDEX, exc_info=True)
        return None
    return float(history["Close"].iloc[-1]) / 100


def _read_bls_cpi() -> pd.Series | None:
    """Monthly CPI-U from the Bureau of Labor Statistics public API."""
    try:
        response = requests.get(
            _BLS_CPI, headers={"User-Agent": "fincent"}, timeout=_TIMEOUT_SECONDS
        )
        rows = response.json()["Results"]["series"][0]["data"]
        return _bls_series(rows)
    except Exception:
        logger.warning("BLS CPI fetch failed", exc_info=True)
        return None


def _bls_series(rows: list[dict]) -> pd.Series | None:
    """Month-indexed values. M13 is an annual average and "-" is a missing month."""
    values = {
        pd.Timestamp(year=int(row["year"]), month=int(row["period"][1:]), day=1): float(row["value"])
        for row in rows
        if row["period"] != "M13" and row["value"] != "-"
    }
    return pd.Series(values).sort_index() if values else None


def _read_fred(series_id: str) -> pd.Series | None:
    url = _FRED_CSV.format(series_id=series_id)
    request = urllib.request.Request(url, headers={"User-Agent": "fincent"})
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            raw = response.read()
        frame = pd.read_csv(io.BytesIO(raw))
    except Exception:
        logger.warning("FRED fetch failed for %s", series_id, exc_info=True)
        return None
    if frame.shape[1] < 2:
        return None
    values = pd.to_numeric(frame.iloc[:, 1], errors="coerce")
    values.index = pd.to_datetime(frame.iloc[:, 0], errors="coerce")
    values = values.dropna()
    return None if values.empty else values
