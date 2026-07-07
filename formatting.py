"""Display formatting shared by the Streamlit pages and persona prompts."""


def fmt_ratio(value: float | None) -> str:
    return "N/A" if value is None else f"{value:,.2f}"


def fmt_pct(value: float | None) -> str:
    """Fraction to percent: 0.0325 -> '3.25%'."""
    return "N/A" if value is None else f"{value * 100:,.2f}%"


def fmt_money(value: float | None) -> str:
    """Compact money formatting: 4.58T, 84.71B, 12.30M."""
    if value is None:
        return "N/A"
    for threshold, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if abs(value) >= threshold:
            return f"{value / threshold:,.2f}{suffix}"
    return f"{value:,.2f}"
