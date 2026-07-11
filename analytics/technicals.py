"""Technical indicators and rule-based trade signals as pure functions.

Everything operates on a pandas Series of closing prices. Indicators return
None when there is not enough history, and the signal/sentiment functions
treat missing indicators as "no opinion" so short histories degrade
gracefully instead of crashing.

These are informational signals from widely used indicator rules — not
financial advice, and the UI says so.
"""

import pandas as pd

RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
RSI_PULLBACK_CEILING = 45
_TRADING_DAYS_PER_MONTH = 21

# Sentiment score thresholds: sum of +1/-1 votes from each indicator.
_BULLISH_SCORE = 2
_BEARISH_SCORE = -2


def rsi(prices: pd.Series, period: int = RSI_PERIOD) -> float | None:
    """Relative Strength Index using Wilder's smoothing. 0-100, or None."""
    if len(prices) < period + 1:
        return None
    delta = prices.diff()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)
    avg_gain = gains.ewm(alpha=1 / period, min_periods=period).mean().iloc[-1]
    avg_loss = losses.ewm(alpha=1 / period, min_periods=period).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    relative_strength = avg_gain / avg_loss
    return float(100 - 100 / (1 + relative_strength))


def sma(prices: pd.Series, window: int) -> float | None:
    """Simple moving average of the last `window` prices, or None."""
    if len(prices) < window:
        return None
    return float(prices.iloc[-window:].mean())


def build_summary(prices: pd.Series) -> dict:
    """All indicators the signal rules need, computed once."""
    return_1mo = None
    if len(prices) > _TRADING_DAYS_PER_MONTH:
        month_ago = prices.iloc[-1 - _TRADING_DAYS_PER_MONTH]
        if month_ago:
            return_1mo = float(prices.iloc[-1] / month_ago - 1)

    return {
        "price": float(prices.iloc[-1]),
        "rsi_14": rsi(prices),
        "sma_20": sma(prices, 20),
        "sma_50": sma(prices, 50),
        "sma_200": sma(prices, 200),
        "return_1mo": return_1mo,
    }


def rsi_zone(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value >= RSI_OVERBOUGHT:
        return "overbought"
    if value <= RSI_OVERSOLD:
        return "oversold"
    return "neutral"


def resample_closes(prices: pd.Series, rule: str | None) -> pd.Series:
    """Downsample closes to bigger bars (e.g. hourly -> 4h). None = as-is."""
    if rule is None:
        return prices
    return prices.resample(rule).last().dropna()


def rsi_signal(value: float | None, bar_label: str) -> str:
    """One-line trader interpretation of an RSI reading on a given bar size."""
    if value is None:
        return (
            f"Not enough {bar_label} bars to compute RSI on this timeframe."
        )
    zone = rsi_zone(value)
    if zone == "overbought":
        return (
            f"On the {bar_label} timeframe, RSI at {value:.0f} is overbought — "
            "momentum is stretched; chasing an entry here is risky and "
            "pullbacks are common."
        )
    if zone == "oversold":
        return (
            f"On the {bar_label} timeframe, RSI at {value:.0f} is oversold — "
            "selling pressure may be exhausted; watch for a bounce or a "
            "basing pattern before acting."
        )
    return (
        f"On the {bar_label} timeframe, RSI at {value:.0f} is in the neutral "
        "zone — no overbought/oversold edge; let the trend decide."
    )


def enter_suggestions(summary: dict) -> list[str]:
    """Rule-based reasons this might be a reasonable entry point."""
    price = summary["price"]
    rsi_14 = summary["rsi_14"]
    sma_50 = summary["sma_50"]
    sma_200 = summary["sma_200"]

    suggestions = []
    if rsi_14 is not None and rsi_14 <= RSI_OVERSOLD:
        suggestions.append(
            f"RSI is oversold at {rsi_14:.0f} — selling pressure may be "
            "exhausted; watch for a mean-reversion bounce."
        )
    if (
        rsi_14 is not None
        and RSI_OVERSOLD < rsi_14 <= RSI_PULLBACK_CEILING
        and sma_200 is not None
        and price > sma_200
    ):
        suggestions.append(
            f"Pullback within a long-term uptrend: RSI has cooled to "
            f"{rsi_14:.0f} while price holds above the 200-day average."
        )
    if (
        sma_50 is not None
        and sma_200 is not None
        and sma_50 > sma_200
        and price > sma_50
        and (rsi_14 is None or rsi_14 < RSI_OVERBOUGHT)
    ):
        suggestions.append(
            "Uptrend intact: the 50-day average is above the 200-day and "
            "price is above both — a trend-following entry."
        )
    return suggestions or [
        "No entry signals right now — the indicators don't show an edge; waiting is a position too."
    ]


def exit_suggestions(summary: dict) -> list[str]:
    """Rule-based reasons to consider trimming or exiting."""
    price = summary["price"]
    rsi_14 = summary["rsi_14"]
    sma_50 = summary["sma_50"]
    sma_200 = summary["sma_200"]

    suggestions = []
    if rsi_14 is not None and rsi_14 >= RSI_OVERBOUGHT:
        suggestions.append(
            f"RSI is overbought at {rsi_14:.0f} — momentum is stretched; "
            "consider trimming or tightening stops."
        )
    if sma_200 is not None and price < sma_200:
        suggestions.append(
            "Price is below the 200-day average — the long-term trend is "
            "broken; rallies may be selling opportunities."
        )
    if sma_50 is not None and sma_200 is not None and sma_50 < sma_200:
        suggestions.append(
            "Death cross: the 50-day average is below the 200-day — the "
            "intermediate trend points down."
        )
    return suggestions or [
        "No exit signals right now — the indicators don't argue for selling."
    ]


def sentiment(summary: dict) -> dict:
    """Aggregate indicator votes into Bullish / Neutral / Bearish.

    Returns {"label", "score", "reasons"} — reasons list one line per vote.
    """
    price = summary["price"]
    rsi_14 = summary["rsi_14"]
    votes: list[tuple[int, str]] = []

    for window in (20, 50, 200):
        average = summary[f"sma_{window}"]
        if average is None:
            continue
        if price > average:
            votes.append((1, f"Price is above the {window}-day average"))
        else:
            votes.append((-1, f"Price is below the {window}-day average"))

    if rsi_14 is not None:
        if rsi_14 > 55:
            votes.append((1, f"RSI at {rsi_14:.0f} shows positive momentum"))
        elif rsi_14 < 45:
            votes.append((-1, f"RSI at {rsi_14:.0f} shows negative momentum"))

    return_1mo = summary["return_1mo"]
    if return_1mo is not None:
        if return_1mo > 0:
            votes.append((1, f"Up {return_1mo:.1%} over the last month"))
        else:
            votes.append((-1, f"Down {abs(return_1mo):.1%} over the last month"))

    score = sum(vote for vote, _ in votes)
    if score >= _BULLISH_SCORE:
        label = "Bullish"
    elif score <= _BEARISH_SCORE:
        label = "Bearish"
    else:
        label = "Neutral"

    return {
        "label": label,
        "score": score,
        "reasons": [reason for _, reason in votes],
        "rsi_zone": rsi_zone(rsi_14),
    }
