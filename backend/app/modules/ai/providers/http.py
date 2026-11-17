import json
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.core.errors import DomainError


class NoRedirect(HTTPRedirectHandler):
    # Do not forward provider credentials to redirect destinations.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def invalid_response() -> DomainError:
    return DomainError(
        503, "AI_RESPONSE_INVALID", "Dịch vụ AI trả kết quả không hợp lệ. Vui lòng thử lại."
    )


def provider_http_error(status: int) -> DomainError:
    # Only HTTP status is inspected; error bodies can contain prompts and credentials.
    errors = {
        400: (
            "AI_PROVIDER_REQUEST_REJECTED",
            "Dịch vụ AI không chấp nhận cấu hình gọi model. "
            "Quản trị viên cần kiểm tra API key, model và API.",
        ),
        401: (
            "AI_PROVIDER_AUTH_FAILED",
            "Dịch vụ AI từ chối xác thực. Quản trị viên cần kiểm tra API key.",
        ),
        403: (
            "AI_PROVIDER_ACCESS_DENIED",
            "Cấu hình hiện tại không được phép truy cập dịch vụ AI.",
        ),
        404: ("AI_MODEL_UNAVAILABLE", "Không truy cập được model hoặc endpoint AI đã cấu hình."),
        429: (
            "AI_PROVIDER_LIMITED",
            "Dịch vụ AI đã giới hạn yêu cầu hoặc hạn mức sử dụng. "
            "Vui lòng thử lại sau hoặc liên hệ quản trị viên.",
        ),
    }
    code, message = errors.get(
        status,
        ("AI_PROVIDER_UNAVAILABLE", "Dịch vụ AI tạm thời không khả dụng. Vui lòng thử lại sau."),
    )
    return DomainError(503, code, message)


def post_json(request: Request, timeout_seconds: int) -> dict:
    try:
        with build_opener(NoRedirect()).open(request, timeout=timeout_seconds) as response:
            raw = response.read(128_001)
        if len(raw) > 128_000:
            raise ValueError("Provider response too large")
        decoded = json.loads(raw)
        if not isinstance(decoded, dict):
            raise ValueError("Provider response must be an object")
        return decoded
    except HTTPError as exc:
        error = provider_http_error(exc.code)
        exc.close()
        raise error from None
    except TimeoutError:
        raise DomainError(
            503, "AI_PROVIDER_TIMEOUT", "Dịch vụ AI phản hồi quá chậm. Vui lòng thử lại."
        ) from None
    except (URLError, OSError):
        raise DomainError(
            503,
            "AI_PROVIDER_UNAVAILABLE",
            "Chưa kết nối được dịch vụ AI. "
            "Bạn có thể tiếp tục dùng các chức năng kho và thử lại sau.",
        ) from None
    except (ValueError, TypeError):
        raise invalid_response() from None
