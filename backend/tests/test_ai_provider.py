import json
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from app.core.config import Settings
from app.core.errors import DomainError
from app.modules.ai.provider import OpenAIProvider, ToolCall, availability
from app.modules.ai.providers.http import NoRedirect


def settings():
    return Settings(
        _env_file=None, ai_provider="openai", ai_model="test-model", ai_api_key="private-test-key"
    )


def fake_http(monkeypatch, payload):
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, size):
            return json.dumps(payload).encode()[:size]

    class Opener:
        def open(self, request, timeout):
            captured.update(url=request.full_url, payload=json.loads(request.data), timeout=timeout)
            return Response()

    monkeypatch.setattr("app.modules.ai.providers.http.build_opener", lambda *args: Opener())
    return captured


def test_responses_api_contract_and_bounded_tools(monkeypatch):
    captured = fake_http(
        monkeypatch,
        {
            "status": "completed",
            "output": [
                {"type": "reasoning", "summary": []},
                {
                    "type": "function_call",
                    "name": "get_stock_by_sku",
                    "arguments": '{"sku":"SP001"}',
                },
            ],
        },
    )
    calls = OpenAIProvider(settings()).plan([], "SP001 còn bao nhiêu?")
    assert calls == [ToolCall("get_stock_by_sku", {"sku": "SP001"})]
    assert captured["url"] == "https://api.openai.com/v1/responses"
    assert captured["payload"]["store"] is False
    assert len(captured["payload"]["tools"]) == 13
    assert captured["payload"]["max_output_tokens"] == 1200
    assert "private-test-key" not in json.dumps(captured["payload"])
    assert NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.example") is None


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"status": "incomplete", "output": []},
        {
            "status": "completed",
            "output": [{"type": "function_call", "name": "x", "arguments": "[]"}],
        },
        {
            "status": "completed",
            "output": [{"type": "function_call", "name": "x", "arguments": "{}"}] * 4,
        },
    ],
)
def test_invalid_provider_output_does_not_become_an_answer(monkeypatch, payload):
    fake_http(monkeypatch, payload)
    with pytest.raises(DomainError) as caught:
        OpenAIProvider(settings()).plan([], "Question")
    assert caught.value.code == "AI_RESPONSE_INVALID"


def test_network_errors_are_sanitized(monkeypatch):
    class Broken:
        def open(self, *args, **kwargs):
            raise URLError("private-provider-payload")

    monkeypatch.setattr("app.modules.ai.providers.http.build_opener", lambda *args: Broken())
    with pytest.raises(DomainError) as caught:
        OpenAIProvider(settings()).plan([], "Question")
    assert caught.value.code == "AI_PROVIDER_UNAVAILABLE"
    assert "private-provider" not in caught.value.message


def test_unconfigured_provider_status_is_explicit():
    assert availability(Settings(_env_file=None))["available"] is False
    assert (
        availability(Settings(_env_file=None, ai_provider="openai", ai_model="model"))["available"]
        is False
    )
    assert availability(Settings(_env_file=None, ai_provider="mock"))["mode"] == "mock"


@pytest.mark.parametrize(
    "status,code",
    [
        (400, "AI_PROVIDER_REQUEST_REJECTED"),
        (401, "AI_PROVIDER_AUTH_FAILED"),
        (403, "AI_PROVIDER_ACCESS_DENIED"),
        (404, "AI_MODEL_UNAVAILABLE"),
        (429, "AI_PROVIDER_LIMITED"),
        (500, "AI_PROVIDER_UNAVAILABLE"),
    ],
)
def test_upstream_errors_are_actionable_and_do_not_expire_user_login(monkeypatch, status, code):
    body = BytesIO(b'{"error":{"message":"private-test-key private-prompt"}}')

    class Broken:
        def open(self, *args, **kwargs):
            raise HTTPError(
                "https://api.openai.com/v1/responses", status, "private-error", {}, body
            )

    monkeypatch.setattr("app.modules.ai.providers.http.build_opener", lambda *args: Broken())
    with pytest.raises(DomainError) as caught:
        OpenAIProvider(settings()).plan([], "Question")
    assert caught.value.code == code
    assert caught.value.status == 503  # Upstream 401 must not become the user's auth failure.
    assert "private" not in caught.value.message
    assert body.closed


def test_provider_timeout_is_distinguishable_from_network_failure(monkeypatch):
    class Slow:
        def open(self, *args, **kwargs):
            raise TimeoutError("private-timeout-payload")

    monkeypatch.setattr("app.modules.ai.providers.http.build_opener", lambda *args: Slow())
    with pytest.raises(DomainError) as caught:
        OpenAIProvider(settings()).plan([], "Question")
    assert caught.value.code == "AI_PROVIDER_TIMEOUT"
