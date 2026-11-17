"""Provider selection; adapters share a typed, read-only planning contract."""

from app.core.config import Settings
from app.core.errors import DomainError
from app.modules.ai.providers.base import Planner, api_key
from app.modules.ai.providers.base import ToolCall as ToolCall
from app.modules.ai.providers.gemini import GeminiProvider
from app.modules.ai.providers.mock import MockProvider
from app.modules.ai.providers.openai import OpenAIProvider


def availability(settings: Settings) -> dict:
    available = settings.ai_provider == "mock" or (
        settings.ai_provider in {"openai", "gemini"}
        and bool(settings.ai_model.strip())
        and bool(api_key(settings))
    )
    return {
        "available": available,
        "mode": settings.ai_provider,
        "message": "Trợ lý sẵn sàng."
        if available
        else "Trợ lý AI chưa được cấu hình. Vui lòng liên hệ quản trị viên.",
    }


def configured_provider(settings: Settings) -> Planner:
    if not availability(settings)["available"]:
        raise DomainError(
            503,
            "AI_NOT_CONFIGURED",
            "Trợ lý AI chưa được cấu hình. Vui lòng liên hệ quản trị viên.",
        )
    if settings.ai_provider == "mock":
        return MockProvider()
    adapters = {"openai": OpenAIProvider, "gemini": GeminiProvider}
    return adapters[settings.ai_provider](settings)
