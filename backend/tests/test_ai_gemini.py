import json

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.errors import DomainError
from app.modules.ai.provider import availability, configured_provider
from app.modules.ai.providers.base import ToolCall
from app.modules.ai.providers.gemini import GeminiProvider
from app.modules.ai.tools import REGISTRY


def settings(**changes):
    return Settings(
        _env_file=None,
        **{
            "ai_provider": "gemini",
            "ai_model": "gemini-3.5-flash-lite",
            "ai_api_key": "private-gemini-key",
            **changes,
        },
    )


def completion(parts, **changes):
    return {
        "candidates": [
            {"finishReason": "STOP", "content": {"role": "model", "parts": parts}, **changes}
        ]
    }


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
            captured.update(
                url=request.full_url,
                payload=json.loads(request.data),
                headers=dict(request.header_items()),
                timeout=timeout,
            )
            return Response()

    monkeypatch.setattr("app.modules.ai.providers.http.build_opener", lambda *args: Opener())
    return captured


def test_native_gemini_uses_header_auth_and_json_schema_tools(monkeypatch):
    captured = fake_http(
        monkeypatch,
        completion(
            [
                {
                    "thoughtSignature": "provider-signature",
                    "functionCall": {"name": "get_stock_by_sku", "args": {"sku": "SP001"}},
                },
            ]
        ),
    )
    calls = GeminiProvider(settings()).plan(
        [{"role": "user", "content": "Câu trước"}], "SP001 còn bao nhiêu?"
    )
    assert calls == [ToolCall("get_stock_by_sku", {"sku": "SP001"})]
    assert (
        captured["url"]
        == "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent"
    )
    assert "?" not in captured["url"]
    assert captured["headers"]["X-goog-api-key"] == "private-gemini-key"
    assert "Authorization" not in captured["headers"]
    payload = captured["payload"]
    assert "private-gemini-key" not in json.dumps(payload)
    assert payload["toolConfig"]["functionCallingConfig"]["mode"] == "AUTO"
    assert payload["generationConfig"]["maxOutputTokens"] == 1200
    declarations = payload["tools"][0]["functionDeclarations"]
    assert {item["name"] for item in declarations} == set(REGISTRY)
    assert all("parametersJsonSchema" in item and "parameters" not in item for item in declarations)
    assert payload["systemInstruction"]["parts"][0]["text"]
    assert len(payload["contents"]) == 1
    assert "Câu trước" in payload["contents"][0]["parts"][0]["text"]


@pytest.mark.parametrize(
    "args,expected",
    [
        ({"limit": 1.0}, {"limit": 1}),
        ({"limit": 1.5}, {"limit": 1.5}),
        ({"limit": True}, {"limit": True}),
    ],
)
def test_gemini_integral_numbers_are_normalized_without_coercing_invalid_values(
    monkeypatch, args, expected
):
    fake_http(monkeypatch, completion([{"functionCall": {"name": "list_low_stock", "args": args}}]))
    call = GeminiProvider(settings()).plan([], "Hàng dưới ngưỡng?")[0]
    assert call.arguments == expected
    if args["limit"] == 1.0 and type(args["limit"]) is float:
        assert type(call.arguments["limit"]) is int
    else:
        with pytest.raises(ValidationError):
            REGISTRY[call.name][0].model_validate(call.arguments)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"promptFeedback": {"blockReason": "SAFETY"}},
        completion([], finishReason="MAX_TOKENS"),
        completion([{"functionCall": {"name": "list_low_stock", "args": []}}]),
        completion([{"functionCall": {"name": "list_low_stock", "args": {}}}] * 4),
        {"candidates": []},
    ],
)
def test_malformed_or_blocked_gemini_output_is_sanitized(monkeypatch, payload):
    fake_http(monkeypatch, payload)
    with pytest.raises(DomainError) as caught:
        GeminiProvider(settings()).plan([], "Question")
    assert caught.value.code == "AI_RESPONSE_INVALID"


def test_gemini_free_text_does_not_become_inventory_evidence(monkeypatch):
    fake_http(monkeypatch, completion([{"text": "SKU còn 999999 chiếc"}]))
    assert GeminiProvider(settings()).plan([], "Question") == []


def test_provider_selection_and_key_isolation():
    config = settings(ai_api_key=None, gemini_api_key="dedicated-gemini-key")
    assert availability(config)["available"] is True
    assert isinstance(configured_provider(config), GeminiProvider)
    config.ai_provider = "openai"
    assert availability(config)["available"] is False


def test_gemini_model_resource_prefix_and_custom_endpoint(monkeypatch):
    captured = fake_http(monkeypatch, completion([{"functionCall": {"name": "list_low_stock"}}]))
    calls = GeminiProvider(
        settings(ai_model="models/gemini-test", ai_base_url="http://127.0.0.1:9000/v1beta")
    ).plan([], "Question")
    assert captured["url"] == "http://127.0.0.1:9000/v1beta/models/gemini-test:generateContent"
    assert calls == [ToolCall("list_low_stock", {})]
