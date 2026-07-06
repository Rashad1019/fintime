"""Valuation and profitability ratios as pure functions.

Every function returns None when the ratio is undefined (zero/negative
denominator or missing input) so the UI can render "N/A" instead of crashing.
"""


def pe_ratio(price: float | None, eps: float | None) -> float | None:
    """Price-to-earnings. Undefined for zero or negative earnings."""
    if price is None or eps is None or eps <= 0:
        return None
    return price / eps


def pb_ratio(price: float | None, book_value_per_share: float | None) -> float | None:
    """Price-to-book. Undefined for zero or negative book value."""
    if price is None or book_value_per_share is None or book_value_per_share <= 0:
        return None
    return price / book_value_per_share


def roe(net_income: float | None, shareholder_equity: float | None) -> float | None:
    """Return on equity. Undefined for zero or negative equity."""
    if net_income is None or shareholder_equity is None or shareholder_equity <= 0:
        return None
    return net_income / shareholder_equity


def debt_to_equity(
    total_debt: float | None, shareholder_equity: float | None
) -> float | None:
    """Debt-to-equity. Undefined for zero or negative equity."""
    if total_debt is None or shareholder_equity is None or shareholder_equity <= 0:
        return None
    return total_debt / shareholder_equity


def profit_margin(net_income: float | None, revenue: float | None) -> float | None:
    """Net profit margin. Undefined for zero or negative revenue."""
    if net_income is None or revenue is None or revenue <= 0:
        return None
    return net_income / revenue


def compute_ratios(fundamentals: dict) -> dict:
    """Build the full ratio set from a fundamentals dict.

    Expected keys (any may be None): price, eps, book_value_per_share,
    net_income, shareholder_equity, total_debt, revenue.
    """
    price = fundamentals.get("price")
    return {
        "pe_ratio": pe_ratio(price, fundamentals.get("eps")),
        "pb_ratio": pb_ratio(price, fundamentals.get("book_value_per_share")),
        "roe": roe(
            fundamentals.get("net_income"), fundamentals.get("shareholder_equity")
        ),
        "debt_to_equity": debt_to_equity(
            fundamentals.get("total_debt"), fundamentals.get("shareholder_equity")
        ),
        "profit_margin": profit_margin(
            fundamentals.get("net_income"), fundamentals.get("revenue")
        ),
    }
