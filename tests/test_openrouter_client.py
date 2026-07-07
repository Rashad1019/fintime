import json

import pytest

from agents import openrouter_client
from agents.openrouter_client import OpenRouterError, ask


class FakeResponse:
    def __init__(self, status_code, content="ok", raw_text=""):
        self.status_code = status_code
        self._content = content
        self.text = raw_text or json.dumps({"error": "fake"})

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


def _patch_post(monkeypatch, responses):
    """Queue fake responses; record which model each call requested."""
    models_called = []

    def fake_post(url, headers=None, json=None, timeout=None):
        models_called.append(json["model"])
        return responses.pop(0)

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
    count = len(openrouter_client.FREE_MODEL_FALLBACKS)
    _patch_post(monkeypatch, [FakeResponse(429) for _ in range(count)])
    with pytest.raises(OpenRouterError, match="unavailable"):
        ask("system", "user")


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
