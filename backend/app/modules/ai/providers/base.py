from dataclasses import dataclass
from typing import Protocol

from app.core.config import Settings


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict


class Planner(Protocol):
    def plan(self, history: list[dict], question: str) -> list[ToolCall]: ...


def api_key(settings: Settings) -> str:
    candidates = (
        [settings.gemini_api_key, settings.ai_api_key]
        if settings.ai_provider == "gemini"
        else [settings.ai_api_key]
    )
    for candidate in candidates:
        if candidate and candidate.get_secret_value().strip():
            return candidate.get_secret_value().strip()
    return ""
