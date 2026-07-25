"""Observability utilities: request IDs, correlation IDs, structured logging."""

import logging
from contextvars import ContextVar
from datetime import datetime, timezone

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    return request_id_var.get(None)


def set_request_id(request_id: str) -> None:
    request_id_var.set(request_id)


class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def _log(self, level: int, event: str, **kwargs):
        extra = {
            "request_id": get_request_id(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **kwargs,
        }
        self.logger.log(level, extra)

    def debug(self, event: str, **kwargs):
        self._log(logging.DEBUG, event, **kwargs)

    def info(self, event: str, **kwargs):
        self._log(logging.INFO, event, **kwargs)

    def warning(self, event: str, **kwargs):
        self._log(logging.WARNING, event, **kwargs)

    def error(self, event: str, **kwargs):
        self._log(logging.ERROR, event, **kwargs)

    def critical(self, event: str, **kwargs):
        self._log(logging.CRITICAL, event, **kwargs)


def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)
