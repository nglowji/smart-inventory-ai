from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.errors import DomainError

LOCAL_ZONE = ZoneInfo("Asia/Ho_Chi_Minh")


def date_bounds(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    if date_to < date_from or (date_to - date_from).days > 365:
        raise DomainError(422, "VALIDATION_ERROR", "Khoảng ngày phải hợp lệ, tối đa 366 ngày.")
    start = datetime.combine(date_from, time.min, LOCAL_ZONE).astimezone(UTC)
    end = datetime.combine(date_to + timedelta(days=1), time.min, LOCAL_ZONE).astimezone(UTC)
    return start, end
