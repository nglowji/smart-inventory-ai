"""Explicit live connection check; never prints keys or submits warehouse data."""

import json
from time import perf_counter

from pydantic import ValidationError

from app.core.config import Settings
from app.core.errors import DomainError
from app.modules.ai.provider import configured_provider
from app.modules.ai.tools import REGISTRY


def check_connection(settings: Settings) -> dict:
    if settings.ai_provider == "mock":
        raise DomainError(
            503,
            "AI_TEST_MODE",
            "Mock mode không xác nhận kết nối model thật. Hãy cấu hình Gemini hoặc OpenAI.",
        )
    provider = configured_provider(settings)
    started = perf_counter()
    calls = provider.plan([], "Liệt kê hàng dưới ngưỡng tối thiểu, tối đa 1 sản phẩm.")
    if not calls or len(calls) > 3:
        raise DomainError(503, "AI_TOOL_CALL_UNVERIFIED", "Model chưa trả công cụ tra cứu hợp lệ.")
    try:
        for call in calls:
            if call.name != "list_low_stock":
                raise ValueError("Unexpected tool")
            REGISTRY[call.name][0].model_validate(call.arguments)
    except (ValidationError, ValueError, TypeError, AttributeError):
        raise DomainError(
            503, "AI_TOOL_CALL_UNVERIFIED", "Model trả công cụ hoặc tham số không đúng yêu cầu."
        ) from None
    return {
        "ok": True,
        "code": "AI_CONNECTED",
        "latency_ms": round((perf_counter() - started) * 1000),
        "tool_calls": [call.name for call in calls],
        "message": "Đã kết nối model thật và xác nhận function calling; chưa gửi dữ liệu kho.",
    }


def main() -> int:
    try:
        result = check_connection(Settings())
    except ValidationError:
        result = {
            "ok": False,
            "code": "AI_CONFIG_INVALID",
            "message": "Cấu hình AI không hợp lệ. Kiểm tra .env local.",
        }
    except DomainError as exc:
        result = {"ok": False, "code": exc.code, "message": exc.message}
    except Exception:
        result = {
            "ok": False,
            "code": "AI_CONNECTION_CHECK_FAILED",
            "message": "Không xác nhận được kết nối AI. Kiểm tra cấu hình và mạng.",
        }
    # ASCII escapes keep JSON parseable on legacy Windows console code pages.
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
