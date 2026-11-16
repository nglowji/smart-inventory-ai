from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.errors import DomainError

LOCAL_ZONE = ZoneInfo("Asia/Ho_Chi_Minh")


def date_bounds(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    if date_to < date_from or (date_to - date_from).days > 365:
        raise DomainError(422, "VALIDATION_ERROR", "Khoảng ngày phải hợp lệ, tối đa 366 ngày.")
    try:
        start = datetime.combine(date_from, time.min, LOCAL_ZONE).astimezone(UTC)
        end = datetime.combine(date_to + timedelta(days=1), time.min, LOCAL_ZONE).astimezone(UTC)
    except (OverflowError, ValueError):
        raise DomainError(
            422, "VALIDATION_ERROR", "Ngày nằm ngoài khoảng thời gian hỗ trợ."
        ) from None
    return start, end


def history_bounds(
    date_from: date | None, date_to: date | None
) -> tuple[datetime | None, datetime | None]:
    if date_from is not None and date_to is not None:
        return date_bounds(date_from, date_to)
    start = date_bounds(date_from, date_from)[0] if date_from is not None else None
    end = date_bounds(date_to, date_to)[1] if date_to is not None else None
    return start, end
