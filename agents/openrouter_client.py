"""Minimal OpenRouter chat-completions client.

Environment (from the shell or a local .env file — never hardcode the key):
  OPENROUTER_API_KEY  required.
  OPENROUTER_MODEL    optional — use exactly this one model.
  OPENROUTER_MODELS   optional — comma-separated rotation list, overriding
                      FREE_MODEL_FALLBACKS. Free-tier models come and go, so
                      this lets you refresh the list without touching code.
"""

import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
REQUEST_TIMEOUT_SECONDS = 120

# Free-tier models get rate-limited upstream minute to minute, so try these
# in order and move to the next on 429 (rate-limited) or 404 (tier removed).
FREE_MODEL_FALLBACKS = [
    "openai/gpt-oss-120b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
]
_RETRYABLE_STATUS_CODES = {404, 429}


class OpenRouterError(Exception):
    """Raised when the OpenRouter call cannot be completed."""


def _models_to_try() -> list[str]:
    single = os.getenv("OPENROUTER_MODEL")
    if single:
        return [single]
    env_list = os.getenv("OPENROUTER_MODELS", "")
    models = [model.strip() for model in env_list.split(",") if model.strip()]
    return models or FREE_MODEL_FALLBACKS


def _call(api_key: str, model: str, system_prompt: str, user_prompt: str):
    return requests.post(
        OPENROUTER_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )


def ask(system_prompt: str, user_prompt: str) -> str:
    """Send one system+user exchange to OpenRouter and return the reply text.

    Models are tried in order (see _models_to_try) until one is not
    rate-limited or removed.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise OpenRouterError(
            "OPENROUTER_API_KEY is not set. Copy .env.example to .env and add your key."
        )

    last_error = None
    for model in _models_to_try():
        try:
            response = _call(api_key, model, system_prompt, user_prompt)
        except requests.RequestException as exc:
            raise OpenRouterError(f"Could not reach OpenRouter: {exc}") from exc

        if response.status_code in _RETRYABLE_STATUS_CODES:
            last_error = (
                f"{model} unavailable (HTTP {response.status_code}): "
                f"{response.text[:200]}"
            )
            logger.warning("Rotating past model: %s", last_error)
            continue
        if response.status_code != 200:
            raise OpenRouterError(
                f"OpenRouter returned HTTP {response.status_code}: {response.text[:300]}"
            )
        try:
            return response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as exc:
            raise OpenRouterError(
                f"Unexpected OpenRouter response shape: {response.text[:300]}"
            ) from exc

    raise OpenRouterError(
        "All models in the rotation are currently unavailable — wait a minute and "
        "retry, or set OPENROUTER_MODELS in .env to a fresh list. "
        f"Last error: {last_error}"
    )
