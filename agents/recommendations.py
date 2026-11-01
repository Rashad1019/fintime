"""Two replacement tickers for a run: one by role, one near the share price.

Prices and names come from the caller. This module does not fetch data and
does not invent fund mechanics that were not in the name or the ticker.
"""

CLOSE_BAND = 0.25

# Liquid funds used as stand-ins. The page fills in live prices.
CANDIDATES = (
    "QQQ",
    "QQQM",
    "SPY",
    "SPLG",
    "VOO",
    "VTI",
    "SCHD",
    "VYM",
    "DGRO",
    "JEPI",
    "JEPQ",
    "VXUS",
    "BND",
    "VNQ",
)

_NASDAQ_INCOME = {"QQQI", "JEPQ", "QYLD"}
_SP_INCOME = {"JEPI", "XYLD", "SPYI"}
_DIVIDEND = {"SCHD", "VYM", "DGRO", "VIG"}

_ROLE_ORDER = {
    "nasdaq_income": ("QQQM", "QQQ"),
    "sp_income": ("SPLG", "SPY", "VOO"),
    "dividend": ("SCHD", "VYM", "DGRO"),
    "etf": ("SPLG", "VTI", "VXUS"),
    "stock": ("SPLG", "VTI", "SCHD"),
}

_ROLE_REASON = {
    "nasdaq_income": "Plain Nasdaq-100 fund in place of a Nasdaq income product.",
    "sp_income": "Plain S&P 500 fund in place of an S&P income product.",
    "dividend": "A dividend fund that does not use an options overlay in the name.",
    "etf": "A broad market fund instead of another specialty product.",
    "stock": "A broad market fund instead of a single company.",
}


def slammed(results: list[dict]) -> bool:
    """True when more than half of the parsed verdicts are Skip."""
    verdicts = [result.get("verdict") for result in results if result.get("verdict")]
    if not verdicts:
        return False
    return verdicts.count("Skip") > len(verdicts) / 2


def classify(ticker: str, name: str | None) -> str:
    """Which replacement list fits this ticker."""
    symbol = ticker.upper()
    label = (name or "").lower()
    if symbol in _NASDAQ_INCOME or ("nasdaq" in label and _income_words(label)):
        return "nasdaq_income"
    if symbol in _SP_INCOME or (
        ("s&p" in label or "sp 500" in label or "s&p 500" in label)
        and _income_words(label)
    ):
        return "sp_income"
    if symbol in _DIVIDEND or "dividend" in label:
        return "dividend"
    if "etf" in label or symbol in CANDIDATES:
        return "etf"
    return "stock"


def pick_replacements(
    ticker: str,
    price: float | None,
    name: str | None,
    quotes: dict[str, dict | None],
) -> list[dict]:
    """Return up to two replacements: a role match and a near-price match.

    Each item is {ticker, name, price, slot, reason}. slot is "role" or "price".
    """
    if price is None or price <= 0:
        return []
    available = _available(quotes, ticker)
    if not available:
        return []

    kind = classify(ticker, name)
    role_ticker = next(
        (symbol for symbol in _ROLE_ORDER[kind] if symbol in available),
        None,
    )
    near_ticker = _nearest(price, available, skip=role_ticker)
    if role_ticker is None:
        role_ticker = near_ticker
        near_ticker = _nearest(price, available, skip=role_ticker)

    picks = []
    if role_ticker is not None:
        picks.append(_item(role_ticker, available[role_ticker], "role", price, ticker, kind))
    if near_ticker is not None and near_ticker != role_ticker:
        picks.append(_item(near_ticker, available[near_ticker], "price", price, ticker, kind))
    return picks


def _income_words(label: str) -> bool:
    return any(word in label for word in ("income", "premium", "covered", "call", "yield"))


def _available(quotes: dict[str, dict | None], subject: str) -> dict[str, dict]:
    kept = {}
    for symbol, quote in quotes.items():
        if symbol.upper() == subject.upper() or not quote:
            continue
        quote_price = quote.get("price")
        if quote_price is None or quote_price <= 0:
            continue
        kept[symbol.upper()] = quote
    return kept


def _nearest(price: float, available: dict[str, dict], skip: str | None) -> str | None:
    pool = [symbol for symbol in available if symbol != skip]
    if not pool:
        return None
    in_band = [symbol for symbol in pool if _gap(price, available[symbol]["price"]) <= CLOSE_BAND]
    choices = in_band or pool
    return min(choices, key=lambda symbol: _gap(price, available[symbol]["price"]))


def _gap(price: float, other: float) -> float:
    return abs(other - price) / price


def _item(symbol: str, quote: dict, slot: str, subject_price: float, subject: str, kind: str) -> dict:
    other = float(quote["price"])
    gap = _gap(subject_price, other)
    name = quote.get("name") or symbol
    if slot == "price":
        if gap <= CLOSE_BAND:
            reason = (
                f"{name} at ${other:,.2f} is {gap:.0%} from {subject} "
                f"at ${subject_price:,.2f}."
            )
        else:
            reason = (
                f"{name} at ${other:,.2f} is the closest share price we checked. "
                f"{subject} is ${subject_price:,.2f}."
            )
    else:
        reason = (
            f"{name} at ${other:,.2f}. {_ROLE_REASON[kind]} "
            f"{subject} is ${subject_price:,.2f}."
        )
    return {
        "ticker": symbol,
        "name": name,
        "price": other,
        "slot": slot,
        "reason": reason,
    }
