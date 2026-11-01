"""Minimal OpenRouter chat-completions client.

Environment (from the shell or a local .env file — never hardcode the key):
  OPENROUTER_API_KEY  required.
  OPENROUTER_MODEL       optional — use exactly this one model. No paid fallback.
  OPENROUTER_MODELS      optional — comma-separated rotation list, overriding
                         FREE_MODEL_FALLBACKS. Free-tier models come and go, so
                         this lets you refresh the list without touching code.
  OPENROUTER_PAID_MODEL  optional — model to try after every free model fails.
                         Defaults to PAID_MODEL_FALLBACK. Set it empty to skip.
"""

import json
import logging
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
CONNECT_TIMEOUT_SECONDS = 10
READ_TIMEOUT_SECONDS = 20
# A read timeout only covers the gap between bytes, and a model that is still
# queued can send keep-alive bytes forever. This caps one model's whole reply.
MODEL_DEADLINE_SECONDS = 40
# After this long, skip the rest of the rotation and go to the last model.
ROTATION_SECONDS = 50

# Free-tier models get rate-limited upstream minute to minute, so try these
# in order and move to the next on any failure that another model could avoid.
# Named free models first. openrouter/free is last: it routes to whatever
# free model is still up when a specific slug has been removed.
FREE_MODEL_FALLBACKS = [
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "thinkingmachines/inkling:free",
    "google/gemma-4-26b-a4b-it:free",
    "openrouter/free",
]
# Used only after the free rotation is exhausted, so credits are spent on a
# persona run that would otherwise fail. Gemma 4 31B is the paid form of the
# first free model: about $0.20 / $0.40 per million tokens.
PAID_MODEL_FALLBACK = "google/gemma-4-31b-it"
_RETRYABLE_STATUS_CODES = {404, 429, 500, 502, 503, 504}


class OpenRouterError(Exception):
    """Raised when the OpenRouter call cannot be completed."""


def _paid_model() -> str | None:
    if "OPENROUTER_PAID_MODEL" in os.environ:
        return os.environ["OPENROUTER_PAID_MODEL"].strip() or None
    return PAID_MODEL_FALLBACK


def _models_to_try() -> list[str]:
    single = os.getenv("OPENROUTER_MODEL")
    if single:
        return [single]
    env_list = os.getenv("OPENROUTER_MODELS", "")
    models = [model.strip() for model in env_list.split(",") if model.strip()]
    models = models or list(FREE_MODEL_FALLBACKS)
    paid = _paid_model()
    if paid and paid not in models:
        models.append(paid)
    return models


def _call(api_key: str, model: str, system_prompt: str, user_prompt: str) -> tuple[int, str]:
    """Return (status code, body), raising requests.Timeout past the deadline."""
    deadline = time.monotonic() + MODEL_DEADLINE_SECONDS
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
        timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
        stream=True,
    )
    with response:
        body = bytearray()
        for chunk in response.iter_content(chunk_size=1024):
            body.extend(chunk)
            if time.monotonic() > deadline:
                raise requests.Timeout(f"No full reply in {MODEL_DEADLINE_SECONDS}s")
    return response.status_code, body.decode("utf-8", errors="replace")


def _reply_text(body: str) -> str | None:
    """The reply in a 200 body, or None when the model sent nothing usable."""
    try:
        content = json.loads(body)["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    return content if content and content.strip() else None


def ask(system_prompt: str, user_prompt: str) -> str:
    """Send one system+user exchange to OpenRouter and return the reply text.

    Free models are tried in order. If every one fails or the rotation runs
    long, the paid fallback is tried once so the run can spend credits instead
    of failing. OPENROUTER_MODEL skips that fallback.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise OpenRouterError(
            "OPENROUTER_API_KEY is not set. Copy .env.example to .env and add your key."
        )

    last_error = None
    models = _models_to_try()
    rotation_ends = time.monotonic() + ROTATION_SECONDS
    for model in models:
        if time.monotonic() > rotation_ends and model != models[-1]:
            continue
        try:
            status, body = _call(api_key, model, system_prompt, user_prompt)
        except requests.RequestException as exc:
            last_error = f"{model} did not answer: {exc}"
            logger.warning("Rotating past model: %s", last_error)
            continue

        if status in _RETRYABLE_STATUS_CODES:
            last_error = f"{model} unavailable (HTTP {status}): {body[:200]}"
            logger.warning("Rotating past model: %s", last_error)
            continue
        if status != 200:
            raise OpenRouterError(f"OpenRouter returned HTTP {status}: {body[:300]}")
        reply = _reply_text(body)
        if reply is not None:
            return reply
        last_error = f"{model} sent no reply: {body[:200]}"
        logger.warning("Rotating past model: %s", last_error)

    paid = _paid_model()
    tried_paid = paid and paid in _models_to_try() and not os.getenv("OPENROUTER_MODEL")
    if tried_paid:
        summary = (
            "Every free model failed, and the paid fallback failed too. "
            "Check OpenRouter credits, or set OPENROUTER_PAID_MODEL to a model "
            "your key can call."
        )
    else:
        summary = (
            "All models in the rotation are currently unavailable — wait a minute "
            "and retry, or set OPENROUTER_MODELS in .env to a fresh list."
        )
    raise OpenRouterError(f"{summary} Last error: {last_error}")
