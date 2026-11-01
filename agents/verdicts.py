"""Pull the structured verdict line out of a persona reply."""

import re

_LINE = re.compile(
    r"\**VERDICT:\s*(BUY NOW|BUY|WAIT|SKIP)\s*\|\s*conviction\s*(\d{1,2})\b\**",
    re.IGNORECASE,
)
_LABELS = {"BUY NOW": "Buy now", "BUY": "Buy now", "WAIT": "Wait", "SKIP": "Skip"}


def parse_verdict(text: str | None) -> tuple[str | None, int | None]:
    """Return (Buy now|Wait|Skip, score) from the reply's verdict line.

    The prompt asks every persona to end with
    `VERDICT: WAIT | conviction 7`. The last match wins. A score outside
    1–10 is ignored.
    """
    if not text:
        return None, None
    found = list(_LINE.finditer(text))
    if not found:
        return None, None
    match = found[-1]
    score = int(match.group(2))
    if not 1 <= score <= 10:
        score = None
    return _LABELS[match.group(1).upper()], score


def without_verdict(text: str) -> str:
    """The reply as a reader should see it, minus the machine-readable line."""
    return _LINE.sub("", text).strip()
