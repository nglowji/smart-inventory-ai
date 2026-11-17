import json
from urllib.request import Request

from app.core.config import Settings
from app.modules.ai.providers.base import ToolCall, api_key
from app.modules.ai.providers.http import invalid_response, post_json
from app.modules.ai.providers.prompts import planner_instructions
from app.modules.ai.tools import definitions


class OpenAIProvider:
    def __init__(self, settings: Settings):
        self.settings = settings

    def plan(self, history: list[dict], question: str) -> list[ToolCall]:
        payload = {
            "model": self.settings.ai_model.strip(),
            "store": False,
            "input": [
                {"role": "system", "content": planner_instructions()},
                *history,
                {"role": "user", "content": question},
            ],
            "tools": [{"type": "function", **tool["function"]} for tool in definitions()],
            "tool_choice": "auto",
            "parallel_tool_calls": True,
            "max_output_tokens": 1200,
        }
        request = Request(
            self.settings.ai_endpoint + "/responses",
            data=json.dumps(payload).encode(),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + api_key(self.settings),
            },
        )
        decoded = post_json(request, self.settings.ai_timeout_seconds)
        try:
            if decoded.get("status") != "completed" or not isinstance(decoded["output"], list):
                raise ValueError("Incomplete provider response")
            calls = [item for item in decoded["output"] if item["type"] == "function_call"]
            if len(calls) > 3:
                raise ValueError("Too many tool calls")
            result = []
            for call in calls:
                if len(call["arguments"]) > 4000:
                    raise ValueError("Arguments too large")
                arguments = json.loads(call["arguments"])
                if not isinstance(arguments, dict) or not isinstance(call["name"], str):
                    raise ValueError("Invalid tool call")
                result.append(ToolCall(call["name"], arguments))
            return result
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise invalid_response() from None
