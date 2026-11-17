import json
import logging
import sys
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    """Only allow known non-secret fields into operational logs."""

    def format(self, record: logging.LogRecord) -> str:
        fields = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        for key in (
            "request_id",
            "method",
            "route",
            "status",
            "duration_ms",
            "actor_id",
            "error_code",
            "error_type",
        ):
            value = getattr(record, key, None)
            if value is not None:
                fields[key] = value
        return json.dumps(fields, ensure_ascii=False)


def configure_logging() -> None:
    # Uvicorn's raw access log includes query strings. Use sanitized structured logs instead.
    logging.getLogger("uvicorn.access").disabled = True
    logger = logging.getLogger("smartinventory.http")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.__stderr__)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
