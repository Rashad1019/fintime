"""Minimal OpenRouter chat-completions client.

Environment (from the shell or a local .env file — never hardcode the key):
  OPENROUTER_API_KEY  required.
  OPENROUTER_MODEL    optional — use exactly this one model, with no other tries.
"""

import json
import logging
import os
import time
from collections.abc import Callable

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
CONNECT_TIMEOUT_SECONDS = 10

# Each try is (model, seconds allowed for its whole reply). One free model
# first, then paid models from different companies, so one outage can't sink
# a run. All three cost under $1 per million tokens written.
PERSONA_ATTEMPTS = [
    ("google/gemma-4-31b-it:free", 30),
    ("google/gemma-4-31b-it", 90),
    ("anthropic/claude-haiku-5.5", 90),
    ("openai/gpt-6-luna", 120),
]
# The explanation holds up the page and has a fallback, so it gets less time.
EXPLANATION_ATTEMPTS = [
    ("google/gemma-4-31b-it:free", 30),
    ("google/gemma-4-31b-it", 30),
]
_RETRYABLE_STATUS_CODES = {404, 429, 500, 502, 503, 504}


class OpenRouterError(Exception):
    """Raised when the OpenRouter call cannot be completed."""


def _call(
    api_key: str, model: str, seconds: float, system_prompt: str, user_prompt: str
) -> tuple[int, str]:
    """Return (status code, body), raising requests.Timeout past the deadline."""
    # The read timeout alone isn't enough: it restarts with every byte, and a
    # queued model can send keep-alive bytes forever.
    deadline = time.monotonic() + seconds
    response = requests.post(
        OPENROUTER_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout=(CONNECT_TIMEOUT_SECONDS, seconds),
        stream=True,
    )
    with response:
        body = bytearray()
        for chunk in response.iter_content(chunk_size=1024):
            body.extend(chunk)
            if time.monotonic() > deadline:
                raise requests.Timeout(f"No full reply in {seconds}s")
    return response.status_code, body.decode("utf-8", errors="replace")


def _reply_text(body: str) -> str | None:
    """The reply in a 200 body, or None when the model sent nothing usable."""
    try:
        content = json.loads(body)["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    return content if content and content.strip() else None


def ask(
    system_prompt: str,
    user_prompt: str,
    attempts: list[tuple[str, float]] = PERSONA_ATTEMPTS,
    on_last_try: Callable[[], None] | None = None,
) -> str:
    """Send one system+user exchange to OpenRouter and return the reply text.

    Tries each model in attempts in order, moving on when one fails or runs out
    of time. on_last_try is called just before the final try starts.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise OpenRouterError(
            "OPENROUTER_API_KEY is not set. Copy .env.example to .env and add your key."
        )

    pinned = os.getenv("OPENROUTER_MODEL")
    if pinned:
        attempts = [(pinned, attempts[-1][1])]

    last_error = None
    for number, (model, seconds) in enumerate(attempts, start=1):
        if on_last_try and number == len(attempts) > 1:
            on_last_try()
        try:
            status, body = _call(api_key, model, seconds, system_prompt, user_prompt)
        except requests.RequestException as exc:
            last_error = f"{model} did not answer: {exc}"
            logger.warning("Moving past model: %s", last_error)
            continue

        if status in _RETRYABLE_STATUS_CODES:
            last_error = f"{model} unavailable (HTTP {status}): {body[:200]}"
            logger.warning("Moving past model: %s", last_error)
            continue
        if status != 200:
            raise OpenRouterError(f"OpenRouter returned HTTP {status}: {body[:300]}")
        reply = _reply_text(body)
        if reply is not None:
            return reply
        last_error = f"{model} sent no reply: {body[:200]}"
        logger.warning("Moving past model: %s", last_error)

    raise OpenRouterError(f"Every model failed. Last error: {last_error}")
