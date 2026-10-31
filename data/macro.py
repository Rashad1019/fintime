"""Public macro series used by the agent prompt. No API key.

Failures stay local: a missing series comes back as None and the persona
prompt shows N/A instead of sinking the analysis.
"""

import io
import logging
import urllib.request

import pandas as pd

logger = logging.getLogger(__name__)

_FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
_TIMEOUT_SECONDS = 15


def fetch_macro() -> dict:
    """10-year Treasury yield and year-over-year CPI, as fractions."""
    return {
        "ten_year_yield": _ten_year_yield(_read_fred("DGS10")),
        "inflation_yoy": inflation_yoy(_read_fred("CPIAUCSL")),
    }


def inflation_yoy(cpi: pd.Series | None) -> float | None:
    """CPI change versus the reading 12 months earlier."""
    if cpi is None or len(cpi) < 13:
        return None
    latest = float(cpi.iloc[-1])
    year_ago = float(cpi.iloc[-13])
    if year_ago == 0:
        return None
    return latest / year_ago - 1


def _ten_year_yield(yields: pd.Series | None) -> float | None:
    """FRED quotes DGS10 in percentage points (4.25 = 4.25%)."""
    if yields is None or len(yields) == 0:
        return None
    return float(yields.iloc[-1]) / 100


def _read_fred(series_id: str) -> pd.Series | None:
    url = _FRED_CSV.format(series_id=series_id)
    request = urllib.request.Request(url, headers={"User-Agent": "fincent"})
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            raw = response.read()
    except Exception:
        logger.warning("FRED fetch failed for %s", series_id, exc_info=True)
        return None
    frame = pd.read_csv(io.BytesIO(raw))
    if frame.shape[1] < 2:
        return None
    values = pd.to_numeric(frame.iloc[:, 1], errors="coerce").dropna()
    if values.empty:
        return None
    return values
