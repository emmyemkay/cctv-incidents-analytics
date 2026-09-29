from __future__ import annotations

import contextvars
import json
import logging
from datetime import datetime, timezone

_request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


def set_request_id(value: str):
    return _request_id.set(value)


def reset_request_id(token):
    _request_id.reset(token)


def get_request_id() -> str:
    return _request_id.get()


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", get_request_id()),
        }
        for key in ("user_id", "event_id", "camera_id", "station", "duration_ms", "status_code"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True, default=str)
