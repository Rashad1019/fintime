"""Plain-English description of a ticker for someone new to investing."""

from agents import openrouter_client

_SYSTEM = (
    "You explain investments to people who have never invested. Use short, "
    "plain sentences and no jargon. If a term is unavoidable, say what it "
    "means. You describe what something is. You never say whether to buy it."
)


def build_prompt(ticker: str, profile: dict) -> str:
    """The facts we have, and how to turn them into a short explanation."""
    facts = [f"Ticker: {ticker}", f"Name: {profile.get('name') or ticker}"]
    for label, key in (
        ("Type", "kind"),
        ("Fund family", "family"),
        ("Category", "category"),
        ("Sector", "sector"),
        ("Industry", "industry"),
        ("Description", "summary"),
    ):
        if profile.get(key):
            facts.append(f"{label}: {profile[key]}")
    return "\n".join(
        [
            *facts,
            "",
            "In three or four short sentences, explain what this is, what you "
            "actually own if you buy it, and who it is usually for.",
            "Use only the facts above and what the name itself tells you. Do "
            "not include prices, returns, or dates. If the facts are thin, "
            "write less rather than guessing.",
        ]
    )


def explain(ticker: str, profile: dict) -> str:
    """Raises OpenRouterError when no model can answer."""
    reply = openrouter_client.ask(
        _SYSTEM, build_prompt(ticker, profile), openrouter_client.EXPLANATION_ATTEMPTS
    )
    return reply.strip()


def fallback_text(ticker: str, profile: dict) -> str:
    """Description to show when no model is available."""
    if profile.get("summary"):
        return profile["summary"]
    kind = profile.get("kind") or "investment"
    if kind != "ETF":
        kind = kind.lower()
    article = "an" if kind[0] in "aeiouAEIOU" else "a"
    return f"{profile.get('name') or ticker} ({ticker}) is {article} {kind}."
