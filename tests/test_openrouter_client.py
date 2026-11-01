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


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(OpenRouterError, match="OPENROUTER_API_KEY"):
        ask("system", "user")


def _attempt_models():
    return [model for model, _ in openrouter_client.PERSONA_ATTEMPTS]


def test_the_order_is_one_free_model_then_three_paid():
    assert [seconds for _, seconds in openrouter_client.PERSONA_ATTEMPTS] == [30, 90, 90, 120]
    models = _attempt_models()
    assert models[0].endswith(":free")
    assert not any(model.endswith(":free") for model in models[1:])
    assert len(set(models)) == 4


def test_moves_to_next_model_on_429(monkeypatch):
    models_called = _patch_post(
        monkeypatch, [FakeResponse(429), FakeResponse(200, content="reply")]
    )
    assert ask("system", "user") == "reply"
    assert models_called == _attempt_models()[:2]


def test_moves_past_removed_model_on_404(monkeypatch):
    models_called = _patch_post(
        monkeypatch, [FakeResponse(404), FakeResponse(200, content="reply")]
    )
    assert ask("system", "user") == "reply"
    assert len(models_called) == 2


def test_all_models_unavailable_raises(monkeypatch):
    models_called = _patch_post(monkeypatch, [FakeResponse(429) for _ in range(4)])
    with pytest.raises(OpenRouterError, match="Every model failed"):
        ask("system", "user")
    assert models_called == _attempt_models()


def test_on_last_try_fires_only_when_the_final_model_starts(monkeypatch):
    calls = []
    _patch_post(monkeypatch, [FakeResponse(429), FakeResponse(200, content="reply")])
    ask("system", "user", on_last_try=lambda: calls.append(1))
    assert calls == []

    _patch_post(
        monkeypatch,
        [FakeResponse(429), FakeResponse(429), FakeResponse(429), FakeResponse(200, content="reply")],
    )
    ask("system", "user", on_last_try=lambda: calls.append(1))
    assert calls == [1]


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


def test_a_model_sending_keep_alive_bytes_is_cut_off_at_its_limit(monkeypatch):
    class Dripping(FakeResponse):
        def iter_content(self, chunk_size):
            while True:
                yield b" "

    models_called = _patch_post(
        monkeypatch, [Dripping(200), FakeResponse(200, content="reply")]
    )
    assert ask("system", "user", [("a/slow", 0.01), ("b/next", 1)]) == "reply"
    assert models_called == ["a/slow", "b/next"]
