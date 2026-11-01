"""Currency conversion for statement figures.

Rates come from the raw chart API, the source that keeps working on hosts
where the yfinance library is blocked.
"""

import logging

from data import DataSourceError, fallback_source

logger = logging.getLogger(__name__)

# Quote currencies that are a fraction of the reporting one: code -> (major, units per major).
_SUBUNITS = {
    "GBp": ("GBP", 100.0),
    "GBX": ("GBP", 100.0),
    "ZAc": ("ZAR", 100.0),
    "ILA": ("ILS", 100.0),
}


def rate(source: str | None, target: str | None) -> float | None:
    """Multiplier from source currency to target, or None if it can't be found.

    Prices can be quoted in a subunit (BP.L trades in pence, GBp), which
    needs its own scale on top of the exchange rate.
    """
    if not source or not target or source == target:
        return 1.0
    major, scale = _SUBUNITS.get(target, (target, 1.0))
    if source == major:
        return scale
    try:
        history = fallback_source.get_history(f"{source}{major}=X", period="5d")
    except DataSourceError:
        logger.warning("FX fetch failed for %s to %s", source, major, exc_info=True)
        return None
    return float(history["Close"].iloc[-1]) * scale
