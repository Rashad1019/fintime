"""Pull the structured verdict line out of a persona reply."""

import re

_LINE = re.compile(
    r"VERDICT:\s*(BUY|HOLD|AVOID)\s*\|\s*conviction\s*(\d{1,2})\b",
    re.IGNORECASE,
)


def parse_verdict(text: str | None) -> tuple[str | None, int | None]:
    """Return (BUY|HOLD|AVOID, score) from the reply's verdict line.

    The prompt asks every persona to end with
    `VERDICT: BUY | conviction 7`. The last match wins. A score outside
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
    return match.group(1).upper(), score
