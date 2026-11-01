import json

import pytest
import requests

from agents import openrouter_client
from agents.openrouter_client import OpenRouterError, ask


class FakeResponse:
    def __init__(self, status_code, content="ok", raw_text=""):
        self.status_code = status_code
        reply = {"choices": [{"message": {"content": content}}]}
        self._body = raw_text or json.dumps(reply if status_code == 200 else {"error": "fake"})

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def iter_content(self, chunk_size):
        yield self._body.encode()


def _patch_post(monkeypatch, responses):
    """Queue fake responses; record which model each call requested."""
    models_called = []

    def fake_post(url, headers=None, json=None, timeout=None, stream=None):
        models_called.append(json["model"])
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(openrouter_client.requests, "post", fake_post)
    return models_called


@pytest.fixture(autouse=True)
def api_key_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    monkeypatch.delenv("OPENROUTER_MODELS", raising=False)


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(OpenRouterError, match="OPENROUTER_API_KEY"):
        ask("system", "user")


def test_rotates_to_next_model_on_429(monkeypatch):
    models_called = _patch_post(
        monkeypatch, [FakeResponse(429), FakeResponse(200, content="reply")]
    )
    assert ask("system", "user") == "reply"
    assert models_called == openrouter_client.FREE_MODEL_FALLBACKS[:2]


def test_rotates_past_removed_model_on_404(monkeypatch):
    models_called = _patch_post(
        monkeypatch, [FakeResponse(404), FakeResponse(200, content="reply")]
    )
    assert ask("system", "user") == "reply"
    assert len(models_called) == 2


def test_all_models_unavailable_raises(monkeypatch):
    count = len(openrouter_client._models_to_try())
    _patch_post(monkeypatch, [FakeResponse(429) for _ in range(count)])
    with pytest.raises(OpenRouterError, match="paid fallback failed"):
        ask("system", "user")


def test_paid_model_is_used_after_free_models_fail(monkeypatch):
    free_count = len(openrouter_client.FREE_MODEL_FALLBACKS)
    models_called = _patch_post(
        monkeypatch,
        [FakeResponse(404) for _ in range(free_count)]
        + [FakeResponse(200, content="paid reply")],
    )
    assert ask("system", "user") == "paid reply"
    assert models_called[-1] == openrouter_client.PAID_MODEL_FALLBACK
    assert models_called[:-1] == openrouter_client.FREE_MODEL_FALLBACKS


def test_empty_paid_model_disables_fallback(monkeypatch):
    monkeypatch.setenv("OPENROUTER_PAID_MODEL", "")
    count = len(openrouter_client.FREE_MODEL_FALLBACKS)
    models_called = _patch_post(
        monkeypatch, [FakeResponse(429) for _ in range(count)]
    )
    with pytest.raises(OpenRouterError, match="currently unavailable"):
        ask("system", "user")
    assert openrouter_client.PAID_MODEL_FALLBACK not in models_called


def test_non_retryable_error_raises_immediately(monkeypatch):
    models_called = _patch_post(monkeypatch, [FakeResponse(401)])
    with pytest.raises(OpenRouterError, match="HTTP 401"):
        ask("system", "user")
    assert len(models_called) == 1


def test_openrouter_model_env_pins_single_model(monkeypatch):
    monkeypatch.setenv("OPENROUTER_MODEL", "some/pinned-model")
    models_called = _patch_post(monkeypatch, [FakeResponse(200, content="reply")])
    assert ask("system", "user") == "reply"
    assert models_called == ["some/pinned-model"]


def test_openrouter_models_env_overrides_rotation_list(monkeypatch):
    monkeypatch.setenv("OPENROUTER_MODELS", "a/one:free, b/two:free")
    models_called = _patch_post(
        monkeypatch, [FakeResponse(429), FakeResponse(200, content="reply")]
    )
    assert ask("system", "user") == "reply"
    assert models_called == ["a/one:free", "b/two:free"]


@pytest.mark.parametrize(
    "failure",
    [
        FakeResponse(500),
        FakeResponse(503),
        requests.Timeout("too slow"),
        requests.ConnectionError("dropped"),
        FakeResponse(200, content=None),
        FakeResponse(200, content="  "),
        FakeResponse(200, raw_text='{"error": {"code": 429}}'),
    ],
)
def test_rotates_past_a_model_that_fails(monkeypatch, failure):
    models_called = _patch_post(monkeypatch, [failure, FakeResponse(200, content="reply")])
    assert ask("system", "user") == "reply"
    assert len(models_called) == 2


def test_a_model_sending_keep_alive_bytes_is_cut_off_at_the_deadline(monkeypatch):
    class Dripping(FakeResponse):
        def iter_content(self, chunk_size):
            while True:
                yield b" "

    monkeypatch.setattr(openrouter_client, "MODEL_DEADLINE_SECONDS", 0.01)
    models_called = _patch_post(
        monkeypatch, [Dripping(200), FakeResponse(200, content="reply")]
    )
    assert ask("system", "user") == "reply"
    assert len(models_called) == 2


def test_a_long_rotation_jumps_to_the_last_model(monkeypatch):
    monkeypatch.setattr(openrouter_client, "ROTATION_SECONDS", -1)
    models_called = _patch_post(monkeypatch, [FakeResponse(200, content="reply")])
    assert ask("system", "user") == "reply"
    assert models_called == [openrouter_client.PAID_MODEL_FALLBACK]
