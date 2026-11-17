import json
from urllib.parse import quote
from urllib.request import Request

from app.core.config import Settings
from app.modules.ai.providers.base import ToolCall, api_key
from app.modules.ai.providers.http import invalid_response, post_json
from app.modules.ai.providers.prompts import planner_instructions
from app.modules.ai.tools import REGISTRY, definitions


class GeminiProvider:
    def __init__(self, settings: Settings):
        self.settings = settings

    def plan(self, history: list[dict], question: str) -> list[ToolCall]:
        declarations = [
            {
                "name": item["function"]["name"],
                "description": item["function"]["description"],
                "parametersJsonSchema": item["function"]["parameters"],
            }
            for item in definitions()
        ]
        parts = []
        if history:
            # One user turn avoids invalid consecutive roles. History remains untrusted text.
            parts.append(
                {
                    "text": "Các câu hỏi trước (chỉ là ngữ cảnh tham khảo): "
                    + "\n".join(item["content"] for item in history)
                }
            )
        parts.append({"text": "Câu hỏi hiện tại: " + question})
        payload = {
            "systemInstruction": {"parts": [{"text": planner_instructions()}]},
            "contents": [{"role": "user", "parts": parts}],
            "tools": [{"functionDeclarations": declarations}],
            "toolConfig": {"functionCallingConfig": {"mode": "AUTO"}},
            "generationConfig": {"candidateCount": 1, "maxOutputTokens": 1200},
        }
        model = self.settings.ai_model.strip().removeprefix("models/")
        request = Request(
            self.settings.ai_endpoint + "/models/" + quote(model, safe="") + ":generateContent",
            data=json.dumps(payload).encode(),
            method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key(self.settings)},
        )
        decoded = post_json(request, self.settings.ai_timeout_seconds)
        try:
            if decoded.get("promptFeedback", {}).get("blockReason"):
                raise ValueError("Blocked provider output")
            candidates = decoded["candidates"]
            if not isinstance(candidates, list) or len(candidates) != 1:
                raise ValueError("Invalid candidate count")
            candidate = candidates[0]
            if candidate.get("finishReason") != "STOP":
                raise ValueError("Incomplete provider response")
            output = candidate["content"]["parts"]
            if not isinstance(output, list):
                raise ValueError("Invalid provider parts")
            calls = [part["functionCall"] for part in output if "functionCall" in part]
            if len(calls) > 3:
                raise ValueError("Too many tool calls")
            result = []
            for call in calls:
                name, arguments = call["name"], call.get("args", {})
                if not isinstance(name, str) or not isinstance(arguments, dict):
                    raise ValueError("Invalid tool call")
                if len(json.dumps(arguments, allow_nan=False)) > 4000:
                    raise ValueError("Arguments too large")
                # Gemini's structured args can represent integral numbers as doubles.
                if name in REGISTRY:
                    properties = REGISTRY[name][0].model_json_schema()["properties"]
                    arguments = {
                        key: int(value)
                        if (
                            properties.get(key, {}).get("type") == "integer"
                            and type(value) is float
                            and value.is_integer()
                        )
                        else value
                        for key, value in arguments.items()
                    }
                result.append(ToolCall(name, arguments))
            return result
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise invalid_response() from None
