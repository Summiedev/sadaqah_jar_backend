"""Observability utilities: request IDs, correlation IDs, structured logging."""

import logging
import re
from collections import defaultdict
from contextvars import ContextVar
from datetime import datetime, timezone
from threading import Lock
from time import perf_counter

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_PATH_ID = re.compile(r"/\d+(?=/|$)")
_PATH_UUID = re.compile(
    r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?=/|$)",
    re.IGNORECASE,
)


class RequestMetrics:
    """Low-overhead in-process request metrics for logs and health tooling.

    Metrics intentionally use normalized paths, so IDs cannot create an
    unbounded label set. They reset with the process; durable historical
    metrics should be scraped into the deployment's metrics backend.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._requests: dict[tuple[str, str, int], int] = defaultdict(int)
        self._duration_seconds: dict[tuple[str, str], float] = defaultdict(float)
        self._errors: dict[str, int] = defaultdict(int)

    @staticmethod
    def normalize_path(path: str) -> str:
        path = _PATH_UUID.sub("/{id}", path)
        return _PATH_ID.sub("/{id}", path)

    def record_request(
        self, method: str, path: str, status_code: int, duration_seconds: float
    ) -> None:
        normalized = self.normalize_path(path)
        with self._lock:
            self._requests[(method, normalized, status_code)] += 1
            self._duration_seconds[(method, normalized)] += duration_seconds
            if status_code >= 500:
                self._errors[normalized] += 1

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "requests": {
                    f"{method} {path} {status}": count
                    for (method, path, status), count in self._requests.items()
                },
                "duration_seconds": {
                    f"{method} {path}": total
                    for (method, path), total in self._duration_seconds.items()
                },
                "server_errors": dict(self._errors),
            }

    def prometheus(self) -> str:
        lines = [
            "# HELP mizan_http_requests_total Total HTTP responses.",
            "# TYPE mizan_http_requests_total counter",
            "# HELP mizan_http_request_duration_seconds_total Total request time.",
            "# TYPE mizan_http_request_duration_seconds_total counter",
            "# HELP mizan_http_server_errors_total HTTP 5xx responses.",
            "# TYPE mizan_http_server_errors_total counter",
        ]
        with self._lock:
            for (method, path, status), count in sorted(self._requests.items()):
                lines.append(
                    f'mizan_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
                )
            for (method, path), total in sorted(self._duration_seconds.items()):
                lines.append(
                    f'mizan_http_request_duration_seconds_total{{method="{method}",path="{path}"}} {total:.6f}'
                )
            for path, count in sorted(self._errors.items()):
                lines.append(
                    f'mizan_http_server_errors_total{{path="{path}"}} {count}'
                )
        return "\n".join(lines) + "\n"


request_metrics = RequestMetrics()


def start_timer() -> float:
    return perf_counter()


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
